import json
from collections.abc import AsyncIterator
from uuid import uuid4
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage


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


async def stream_chat(
    *,
    graph,
    thread_id: str,
    lc_messages: list[tuple[str, str]],
) -> AsyncIterator[str]:
    msg_id = f"msg_{uuid4().hex}"
    text_id = f"t_{uuid4().hex}"
    yield sse({"type": "start", "messageId": msg_id})
    yield sse({"type": "start-step"})
    yield sse({"type": "text-start", "id": text_id})

    tool_args_buffer: dict[str, str] = {}
    tool_names: dict[str, str] = {}
    announced_start: set[str] = set()
    announced_input: set[str] = set()

    # Subagent linkage: a non-empty langgraph namespace identifies events from
    # inside a subgraph. We map each namespace to the parent dispatcher's
    # tool_call_id so the UI can group inner tool calls under the parent card.
    parent_by_namespace: dict[tuple, str] = {}
    current_dispatch_id: str | None = None

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
                and len(event) == 2
                and isinstance(event[0], tuple)
                and isinstance(event[1], tuple)
                and len(event[1]) == 2
            ):
                namespace, (chunk, meta) = event
            elif isinstance(event, tuple) and len(event) == 2:
                chunk, meta = event
                namespace = ()
            else:
                continue
            node = (meta or {}).get("langgraph_node")
            is_top_level = not namespace

            # First time we see events from a subgraph — lock in its parent.
            if namespace and namespace not in parent_by_namespace and current_dispatch_id:
                parent_by_namespace[namespace] = current_dispatch_id

            if isinstance(chunk, AIMessageChunk):
                # User-visible text only from the top-level model — subagents'
                # internal LLM tokens stay inside their tool result.
                if is_top_level and node == "model" and chunk.content:
                    yield sse({"type": "text-delta", "id": text_id, "delta": chunk.content})

                for tcc in (chunk.tool_call_chunks or []):
                    cid = tcc.get("id")
                    if not cid:
                        continue
                    name = tcc.get("name")
                    args = tcc.get("args")
                    if name and cid not in tool_names:
                        tool_names[cid] = name
                        ev = _start(cid, name, namespace)
                        if ev:
                            yield ev
                    if args:
                        tool_args_buffer[cid] = tool_args_buffer.get(cid, "") + args

            if isinstance(chunk, AIMessage):
                for tc in (getattr(chunk, "tool_calls", None) or []):
                    cid = tc.get("id")
                    if not cid or cid in announced_input:
                        continue
                    name = tc.get("name") or tool_names.get(cid, "tool")
                    args = tc.get("args") or {}

                    # Track dispatcher invocations at top level so we can
                    # attribute subsequent subgraph events to them.
                    if is_top_level and name in DISPATCHER_TOOLS:
                        current_dispatch_id = cid

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
                        except Exception:
                            parsed = {"_raw": raw}
                    ev = _start(cid, name, namespace)
                    if ev:
                        yield ev
                    yield _input_available(cid, name, parsed, namespace)
                    announced_input.add(cid)
                if cid:
                    yield _output_available(cid, _coerce_output(chunk.content), namespace)
                    if is_top_level and cid == current_dispatch_id:
                        current_dispatch_id = None
    except Exception as e:
        yield sse({"type": "error", "errorText": str(e)})
    finally:
        yield sse({"type": "text-end", "id": text_id})
        yield sse({"type": "finish-step"})
        yield sse({"type": "finish"})
        yield "data: [DONE]\n\n"
