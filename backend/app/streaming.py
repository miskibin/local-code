import asyncio
import json
import time
from collections.abc import AsyncIterator
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command
from loguru import logger

from app.artifact_store import get_artifact, persist_tool_artifact
from app.db import async_session
from app.models import MessageTrace
from app.tasks import coerce_lc_content
from app.utils import coerce_output


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n"


# Tool names that, when called at top level, dispatch a subagent. Inner tool
# events emitted from within the resulting subgraph get tagged with the
# dispatcher's tool_call_id so the UI can nest them.
DISPATCHER_TOOLS = {"task"}


async def _read_summary_cutoff(checkpointer, thread_id: str) -> int | None:
    """Snapshot `_summarization_event.cutoff_index` from the checkpoint, or None.

    Uses the raw checkpointer rather than `graph.aget_state` because the
    summarization event is a `PrivateStateAttr` and may be filtered out of
    the StateSnapshot exposed by the runnable.
    """
    if checkpointer is None:
        return None
    try:
        tup = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
    except Exception as e:  # noqa: BLE001 -- best-effort diagnostic, never crash stream
        logger.debug(f"summary snapshot fail thread={thread_id} err={e!r}")
        return None
    if tup is None:
        return None
    cp = getattr(tup, "checkpoint", None)
    if not isinstance(cp, dict):
        return None
    channel_values = cp.get("channel_values") or {}
    evt = channel_values.get("_summarization_event")
    if isinstance(evt, dict):
        idx = evt.get("cutoff_index")
        if isinstance(idx, int):
            return idx
    return None


async def stream_chat(  # noqa: PLR0912, PLR0915 -- protocol assembler; splits would fragment SSE state
    *,
    graph,
    thread_id: str,
    lc_messages: list,
    owner_id: str,
    session_id: str | None = None,
    resume_value: object = None,
    context_max_tokens: int | None = None,
    model_id: str | None = None,
    checkpointer=None,
    langfuse_handler: object = None,
) -> AsyncIterator[str]:
    msg_id = f"msg_{uuid4().hex}"
    logger.info(f"stream start thread={thread_id} msg_id={msg_id} input_msgs={len(lc_messages)}")
    yield sse({"type": "start", "messageId": msg_id})
    yield sse({"type": "start-step"})
    pre_summary_cutoff = await _read_summary_cutoff(checkpointer, thread_id)

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
        "skipped_events": 0,
        "empty_ai_chunks": 0,
    }
    # Capture the last AIMessage(Chunk) terminal metadata so we can tell
    # finish_reason (STOP / MAX_TOKENS / SAFETY / RECITATION / OTHER) and
    # token usage at end-of-stream. Gemini Flash-Lite often returns SAFETY or
    # MAX_TOKENS silently; without this the client just sees an empty turn.
    last_finish_reason: str | None = None
    last_response_metadata: dict | None = None
    last_usage_metadata: dict | None = None
    total_input_tokens = 0
    total_output_tokens = 0
    ai_message_id: str | None = None
    stream_start = time.monotonic()

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

    graph_input: object = (
        Command(resume=resume_value) if resume_value is not None else {"messages": lc_messages}
    )
    try:
        astream_config: dict = {"configurable": {"thread_id": thread_id, "owner_id": owner_id}}
        if langfuse_handler is not None:
            astream_config["callbacks"] = [langfuse_handler]
            astream_config["metadata"] = {
                "langfuse_session_id": session_id or thread_id,
                "langfuse_user_id": session_id or thread_id,
            }
        async for event in graph.astream(
            graph_input,
            stream_mode="messages",
            subgraphs=True,
            config=astream_config,
        ):
            # stream_mode="messages" with subgraphs=True yields
            #   (namespace_tuple, (chunk, meta)).
            if (
                isinstance(event, tuple)
                and len(event) == 2  # noqa: PLR2004 -- (namespace, (chunk, meta))
                and isinstance(event[0], tuple)
                and isinstance(event[1], tuple)
                and len(event[1]) == 2  # noqa: PLR2004 -- (chunk, meta)
            ):
                namespace, (chunk, meta) = event
            else:
                # Bumped from DEBUG: an unrecognised payload shape means we are
                # silently dropping something langgraph emitted. Visible by
                # default so we notice format drift.
                counters["skipped_events"] += 1
                logger.warning(
                    f"stream event skipped thread={thread_id} payload_type={type(event).__name__} "
                    f"repr={str(event)[:200]!r}"
                )
                continue
            node = (meta or {}).get("langgraph_node")
            is_top_level = not namespace

            # Snapshot terminal metadata only from the *parent* model node.
            # Subagents emit their own terminal chunks (often with SAFETY /
            # MAX_TOKENS), and conflating them with the parent turn produces
            # false-positive ANOMALY warnings on a state the user never saw.
            if isinstance(chunk, (AIMessage, AIMessageChunk)) and is_top_level and node == "model":
                rmd = getattr(chunk, "response_metadata", None) or {}
                if rmd:
                    last_response_metadata = rmd
                    fr = rmd.get("finish_reason") or rmd.get("stop_reason")
                    if fr:
                        last_finish_reason = str(fr)
                umd = getattr(chunk, "usage_metadata", None)
                if umd:
                    last_usage_metadata = dict(umd) if not isinstance(umd, dict) else umd
                _aimid = getattr(chunk, "id", None)
                if _aimid:
                    ai_message_id = _aimid
            # Aggregate token counts across all model calls in this turn (top
            # level + subagents). Streaming usually delivers usage_metadata only
            # on the final chunk per model call, so summing those covers the
            # full task cost.
            if isinstance(chunk, (AIMessage, AIMessageChunk)):
                umd_any = getattr(chunk, "usage_metadata", None)
                if umd_any:
                    total_input_tokens += int(umd_any.get("input_tokens") or 0)
                    total_output_tokens += int(umd_any.get("output_tokens") or 0)
            if (
                isinstance(chunk, (AIMessage, AIMessageChunk))
                and is_top_level
                and node == "model"
                and isinstance(chunk, AIMessageChunk)
                and not chunk.content
                and not (chunk.tool_call_chunks or [])
            ):
                counters["empty_ai_chunks"] += 1

            # First time we see events from a subgraph — lock in its parent.
            if namespace and namespace not in parent_by_namespace and current_dispatch_id:
                parent_by_namespace[namespace] = current_dispatch_id

            if isinstance(chunk, AIMessageChunk):
                # User-visible text only from the top-level model — subagents'
                # internal LLM tokens stay inside their tool result.
                # langchain-google-genai emits content as list[dict] blocks
                # (e.g. [{"type":"text","text":"..."}, {"extras":{"signature":...}}]);
                # the Vercel AI SDK 6 text-delta schema requires `delta: string`,
                # so flatten via the shared helper. Empty results (signature-only
                # blocks) are skipped to avoid opening empty text parts.
                if is_top_level and node == "model" and chunk.content:
                    delta_text = coerce_lc_content(chunk.content)
                    if delta_text:
                        if text_id is None:
                            yield _open_text()
                        yield sse({"type": "text-delta", "id": text_id, "delta": delta_text})
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
                        # Lock in dispatcher id here so subgraph events that
                        # arrive before the parent AIMessage still get a
                        # parentToolCallId attached via parent_by_namespace.
                        if is_top_level and name in DISPATCHER_TOOLS:
                            current_dispatch_id = cid
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
                # Diagnostic: surface tool observation length + first 300 chars of
                # write_todos content (it accumulates "status: completed" markers
                # which can prompt the model to emit STOP without final synthesis).
                _tname = tool_names.get(cid or "") or getattr(chunk, "name", "")
                _content_repr = repr(getattr(chunk, "content", ""))[:300]
                logger.debug(
                    f"tool_observation thread={thread_id} cid={cid} name={_tname!r} "
                    f"len={len(_content_repr)} content={_content_repr}"
                )
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
                    output = coerce_output(chunk.content)
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
                                        artifact=artifact,
                                        session_id=session_id,
                                        owner_id=owner_id,
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
            f"stream cancelled thread={thread_id} last_step={last_step} counters={counters} "
            f"finish_reason={last_finish_reason!r} usage={last_usage_metadata!r}"
        )
        raise
    except Exception as e:  # noqa: BLE001 -- protocol boundary; surface as SSE error so client gets a clean finish
        err_text = f"{type(e).__name__}: {e}"
        logger.exception(
            f"stream error thread={thread_id} last_step={last_step} counters={counters} "
            f"finish_reason={last_finish_reason!r} usage={last_usage_metadata!r} "
            f"err={err_text!r}"
        )
        logger.warning(f"stream emitting SSE error to client thread={thread_id} text={err_text!r}")
        yield sse({"type": "error", "errorText": err_text})
    finally:
        # Detect silent failures the upstream model gave us:
        #   - empty turn (no text + no tool output): model returned nothing
        #   - finish_reason == SAFETY/RECITATION/MAX_TOKENS: blocked / truncated
        #   - orphan tool arg buffers: tool call started, never finished
        empty_turn = counters["text_chunks"] == 0 and counters["tool_outputs"] == 0
        orphan_tool_cids = [c for c in tool_args_buffer if c not in announced_input]
        truncated_or_blocked = last_finish_reason and last_finish_reason.upper() not in {
            "STOP",
            "END_TURN",
            "TOOL_CALLS",
            "TOOL_USE",
            "FUNCTION_CALL",
        }
        if empty_turn or truncated_or_blocked or orphan_tool_cids:
            logger.warning(
                f"stream end ANOMALY thread={thread_id} empty_turn={empty_turn} "
                f"finish_reason={last_finish_reason!r} orphan_tool_cids={orphan_tool_cids} "
                f"counters={counters} response_metadata={last_response_metadata!r} "
                f"usage={last_usage_metadata!r}"
            )
        logger.info(
            f"stream end thread={thread_id} last_step={last_step} counters={counters} "
            f"finish_reason={last_finish_reason!r} usage={last_usage_metadata!r}"
        )
        closed = _close_text()
        if closed:
            yield closed
        if langfuse_handler is not None:
            trace_id = getattr(langfuse_handler, "last_trace_id", None)
            if trace_id:
                from langfuse import get_client  # noqa: PLC0415

                trace_url = get_client().get_trace_url(trace_id=trace_id)
                yield sse(
                    {
                        "type": "data-trace",
                        "id": f"trace_{msg_id}",
                        "data": {
                            "traceId": trace_id,
                            "messageId": ai_message_id,
                            "traceUrl": trace_url,
                        },
                    }
                )
                if ai_message_id and session_id:
                    async with async_session() as s:
                        await s.merge(
                            MessageTrace(
                                ai_message_id=ai_message_id,
                                session_id=session_id,
                                trace_id=trace_id,
                            )
                        )
                        await s.commit()
        # Always emit one data-usage part per turn. durationMs is meaningful
        # even when the model returned no usage_metadata (e.g. local Ollama),
        # and the client hides zero-token columns in the rendered row.
        duration_ms = int((time.monotonic() - stream_start) * 1000)
        usage_data: dict = {
            "inputTokens": total_input_tokens,
            "outputTokens": total_output_tokens,
            "durationMs": duration_ms,
        }
        if context_max_tokens:
            usage_data["contextMaxTokens"] = context_max_tokens
        if model_id:
            usage_data["modelId"] = model_id
        yield sse(
            {
                "type": "data-usage",
                "id": f"usage_{msg_id}",
                "data": usage_data,
            }
        )
        # Detect auto-summarization (or `compact_conversation` tool call): the
        # cutoff_index moves forward when SummarizationMiddleware compacts the
        # history. Surface it once per turn so the UI can render a notice.
        post_summary_cutoff = await _read_summary_cutoff(checkpointer, thread_id)
        if post_summary_cutoff is not None and post_summary_cutoff != pre_summary_cutoff:
            logger.info(
                f"summary fired thread={thread_id} "
                f"prev_cutoff={pre_summary_cutoff} new_cutoff={post_summary_cutoff}"
            )
            yield sse(
                {
                    "type": "data-summary",
                    "id": f"summary_{msg_id}",
                    "data": {
                        "cutoffIndex": post_summary_cutoff,
                        "previousCutoffIndex": pre_summary_cutoff,
                    },
                }
            )
        yield sse({"type": "finish-step"})
        yield sse({"type": "finish"})
        yield "data: [DONE]\n\n"
