import json
from collections.abc import AsyncIterator
from uuid import uuid4
from langchain_core.messages import AIMessageChunk


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n"


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
    try:
        async for chunk, meta in graph.astream(
            {"messages": lc_messages},
            stream_mode="messages",
            config={"configurable": {"thread_id": thread_id}},
        ):
            if (
                isinstance(chunk, AIMessageChunk)
                and meta.get("langgraph_node") == "model"
                and chunk.content
            ):
                yield sse({"type": "text-delta", "id": text_id, "delta": chunk.content})
    except Exception as e:
        yield sse({"type": "error", "errorText": str(e)})
    finally:
        yield sse({"type": "text-end", "id": text_id})
        yield sse({"type": "finish-step"})
        yield sse({"type": "finish"})
        yield "data: [DONE]\n\n"
