import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from loguru import logger

from app.artifact_store import get_artifact, persist_tool_artifact


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n"


# Tool names that, when called at top level, dispatch a subagent. Inner tool
# events emitted from within the resulting subgraph get tagged with the
# dispatcher's tool_call_id so the UI can nest them.
DISPATCHER_TOOLS = {"task"}


def _coerce_output(content) -> object:
    if isinstance(content, (str, int, float, bool)) or content is None:
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(str(c.get("text", "")))
            else:
                parts.append(str(c))
        return "".join(parts)
    return str(content)


async def stream_chat(  # noqa: PLR0912, PLR0915 -- protocol assembler; splits would fragment SSE state
    *,
    graph,
    thread_id: str,
    lc_messages: list,
    session_id: str | None = None,
) -> AsyncIterator[str]:
    msg_id = f"msg_{uuid4().hex}"
    logger.info(f"stream start thread={thread_id} msg_id={msg_id} input_msgs={len(lc_messages)}")
    yield sse({"type": "start", "messageId": msg_id})
    yield sse({"type": "start-step"})

    # Each top-level text run gets its own id so the AI SDK keeps it as a
    # separate part. Reusing one id across tool calls makes the SDK merge all
    # deltas into a single part anchored at its first appearance, which loses
    # the actual text/tool interleaving in the rendered message.
    text_id: str | None = None

    tool_args_buffer: dict[str, str] = {}
    tool_names: dict[str, str] = {}
    announced_start: set[str] = set()
    announced_input: set[str] = set()

    # Subagent linkage: a non-empty langgraph namespace identifies events from
    # inside a subgraph. We map each namespace to the parent dispatcher's
    # tool_call_id so the UI can group inner tool calls under the parent card.
    parent_by_namespace: dict[tuple, str] = {}
    current_dispatch_id: str | None = None

    # Diagnostics: track where the stream was when it ends/cancels/errors.
    last_step = "init"
    counters = {
        "text_chunks": 0,
        "tool_calls_started": 0,
        "tool_outputs": 0,
        "subagent_dispatches": 0,
    }

    def _provider_md(namespace: tuple) -> dict | None:
        # AI SDK 6 schema: providerMetadata is Record<string, Record<string, JsonValue>>.
        # Wrap our linkage info under a "subagent" provider key so it validates
        # and reaches the client message part.
        if not namespace:
            return None
        sub: dict = {"namespace": list(namespace)}
        parent = parent_by_namespace.get(namespace)
        if parent:
            sub["parentToolCallId"] = parent
        return {"subagent": sub}

    def _start(cid: str, name: str, namespace: tuple) -> str | None:
        if cid in announced_start:
            return None
        announced_start.add(cid)
        evt: dict = {
            "type": "tool-input-start",
            "toolCallId": cid,
            "toolName": name,
        }
        md = _provider_md(namespace)
        if md:
            evt["providerMetadata"] = md
        return sse(evt)

    def _input_available(cid: str, name: str, args: object, namespace: tuple) -> str:
        evt: dict = {
            "type": "tool-input-available",
            "toolCallId": cid,
            "toolName": name,
            "input": args,
        }
        md = _provider_md(namespace)
        if md:
            evt["providerMetadata"] = md
        return sse(evt)

    def _output_available(cid: str, output: object, namespace: tuple) -> str:
        evt: dict = {
            "type": "tool-output-available",
            "toolCallId": cid,
            "output": output,
        }
        md = _provider_md(namespace)
        if md:
            evt["providerMetadata"] = md
        return sse(evt)

    def _output_error(cid: str, error_text: str, namespace: tuple) -> str:
        evt: dict = {
            "type": "tool-output-error",
            "toolCallId": cid,
            "errorText": error_text,
        }
        md = _provider_md(namespace)
        if md:
            evt["providerMetadata"] = md
        return sse(evt)

    def _open_text() -> str:
        nonlocal text_id
        text_id = f"t_{uuid4().hex}"
        return sse({"type": "text-start", "id": text_id})

    def _close_text() -> str | None:
        nonlocal text_id
        if text_id is None:
            return None
        ev = sse({"type": "text-end", "id": text_id})
        text_id = None
        return ev

    try:
        async for event in graph.astream(
            {"messages": lc_messages},
            stream_mode="messages",
            subgraphs=True,
            config={"configurable": {"thread_id": thread_id}},
        ):
            # subgraphs=True for stream_mode="messages" yields
            #   (namespace_tuple, (chunk, meta)).
            # Legacy (no subgraphs) yields (chunk, meta).
            if (
                isinstance(event, tuple)
                and len(event) == 2  # noqa: PLR2004 -- (namespace, (chunk, meta))
                and isinstance(event[0], tuple)
                and isinstance(event[1], tuple)
                and len(event[1]) == 2  # noqa: PLR2004 -- (chunk, meta)
            ):
                namespace, (chunk, meta) = event
            elif isinstance(event, tuple) and len(event) == 2:  # noqa: PLR2004 -- legacy (chunk, meta)
                chunk, meta = event
                namespace = ()
            else:
                logger.debug(
                    f"stream event skipped thread={thread_id} payload_type={type(event).__name__}"
                )
                continue
            node = (meta or {}).get("langgraph_node")
            is_top_level = not namespace
            logger.debug(
                f"event thread={thread_id} kind={type(chunk).__name__} "
                f"node={node} ns={list(namespace)}"
            )

            # First time we see events from a subgraph — lock in its parent.
            if namespace and namespace not in parent_by_namespace and current_dispatch_id:
                parent_by_namespace[namespace] = current_dispatch_id

            if isinstance(chunk, AIMessageChunk):
                # User-visible text only from the top-level model — subagents'
                # internal LLM tokens stay inside their tool result.
                if is_top_level and node == "model" and chunk.content:
                    if text_id is None:
                        yield _open_text()
                    yield sse({"type": "text-delta", "id": text_id, "delta": chunk.content})
                    counters["text_chunks"] += 1
                    last_step = "text"

                for tcc in chunk.tool_call_chunks or []:
                    cid = tcc.get("id")
                    if not cid:
                        logger.warning(f"tool_call_chunk missing id thread={thread_id} chunk={tcc}")
                        continue
                    name = tcc.get("name")
                    args = tcc.get("args")
                    if name and cid not in tool_names:
                        tool_names[cid] = name
                        if is_top_level:
                            closed = _close_text()
                            if closed:
                                yield closed
                        ev = _start(cid, name, namespace)
                        if ev:
                            yield ev
                            counters["tool_calls_started"] += 1
                            last_step = f"tool_call_start:{name}"
                    if args:
                        tool_args_buffer[cid] = tool_args_buffer.get(cid, "") + args

            if isinstance(chunk, AIMessage):
                for tc in getattr(chunk, "tool_calls", None) or []:
                    cid = tc.get("id")
                    if not cid:
                        logger.warning(f"tool_call missing id thread={thread_id} tc={tc}")
                        continue
                    if cid in announced_input:
                        continue
                    name = tc.get("name") or tool_names.get(cid, "tool")
                    args = tc.get("args") or {}

                    # Track dispatcher invocations at top level so we can
                    # attribute subsequent subgraph events to them.
                    if is_top_level and name in DISPATCHER_TOOLS:
                        current_dispatch_id = cid
                        counters["subagent_dispatches"] += 1
                        last_step = f"dispatcher_start:{name}"
                        logger.debug(f"dispatcher start cid={cid} name={name}")
                    else:
                        last_step = f"tool_call_start:{name}"

                    if is_top_level:
                        closed = _close_text()
                        if closed:
                            yield closed
                    ev = _start(cid, name, namespace)
                    if ev:
                        yield ev
                    yield _input_available(cid, name, args, namespace)
                    announced_input.add(cid)

            if isinstance(chunk, ToolMessage):
                cid = chunk.tool_call_id
                if cid and cid not in announced_input:
                    name = tool_names.get(cid) or getattr(chunk, "name", None) or "tool"
                    raw = tool_args_buffer.get(cid, "")
                    parsed: object = {}
                    if raw:
                        try:
                            parsed = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"tool args json decode fail cid={cid} thread={thread_id} "
                                f"raw={raw[:200]!r}"
                            )
                            parsed = {"_raw": raw}
                    if is_top_level:
                        closed = _close_text()
                        if closed:
                            yield closed
                    ev = _start(cid, name, namespace)
                    if ev:
                        yield ev
                    yield _input_available(cid, name, parsed, namespace)
                    announced_input.add(cid)
                if cid:
                    output = _coerce_output(chunk.content)
                    name = tool_names.get(cid) or getattr(chunk, "name", None) or "tool"
                    if is_top_level:
                        closed = _close_text()
                        if closed:
                            yield closed
                    if getattr(chunk, "status", None) == "error":
                        yield _output_error(cid, str(output), namespace)
                    else:
                        yield _output_available(cid, output, namespace)
                        artifact = getattr(chunk, "artifact", None)
                        if isinstance(artifact, dict) and artifact:
                            artifact_id = artifact.get("id")
                            try:
                                if artifact_id:
                                    row = await get_artifact(artifact_id)
                                else:
                                    row = await persist_tool_artifact(
                                        artifact=artifact, session_id=session_id
                                    )
                            except Exception:
                                logger.exception(
                                    f"artifact persist fail cid={cid} thread={thread_id}"
                                )
                                raise
                            if row is None:
                                continue
                            data: dict = {
                                "toolCallId": cid,
                                "artifactId": row.id,
                                "kind": row.kind,
                                "title": row.title,
                                "summary": row.summary,
                                "updatedAt": row.updated_at.isoformat(),
                            }
                            md = _provider_md(namespace)
                            if md:
                                data["providerMetadata"] = md
                            yield sse(
                                {
                                    "type": "data-artifact",
                                    "id": row.id,
                                    "data": data,
                                }
                            )
                    counters["tool_outputs"] += 1
                    last_step = f"tool_output:{name}"
                    if is_top_level and cid == current_dispatch_id:
                        logger.debug(f"dispatcher done cid={cid}")
                        last_step = f"dispatcher_done:{name}"
                        current_dispatch_id = None
    except asyncio.CancelledError:
        logger.warning(
            f"stream cancelled thread={thread_id} last_step={last_step} counters={counters}"
        )
        raise
    except Exception as e:  # noqa: BLE001 -- protocol boundary; surface as SSE error so client gets a clean finish
        logger.exception(
            f"stream error thread={thread_id} last_step={last_step} counters={counters}"
        )
        yield sse({"type": "error", "errorText": str(e)})
    finally:
        logger.info(f"stream end thread={thread_id} last_step={last_step} counters={counters}")
        closed = _close_text()
        if closed:
            yield closed
        yield sse({"type": "finish-step"})
        yield sse({"type": "finish"})
        yield "data: [DONE]\n\n"
