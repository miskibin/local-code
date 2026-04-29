import json
import time
from collections.abc import AsyncIterator
from uuid import uuid4


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n"


async def stream_static_text(text: str, *, model_id: str | None = None) -> AsyncIterator[str]:
    """Synthesize a Vercel AI SDK 6 UI message stream that emits a single text part.

    Mirrors the start/start-step/text-*/finish-step/finish/[DONE] envelope used
    by `app.streaming.stream_chat` so the frontend renders it identically.
    """
    msg_id = f"msg_{uuid4().hex}"
    text_id = f"t_{uuid4().hex}"
    start = time.monotonic()
    yield _sse({"type": "start", "messageId": msg_id})
    yield _sse({"type": "start-step"})
    yield _sse({"type": "text-start", "id": text_id})
    yield _sse({"type": "text-delta", "id": text_id, "delta": text})
    yield _sse({"type": "text-end", "id": text_id})
    duration_ms = int((time.monotonic() - start) * 1000)
    usage: dict = {"inputTokens": 0, "outputTokens": 0, "durationMs": duration_ms}
    if model_id:
        usage["modelId"] = model_id
    yield _sse({"type": "data-usage", "id": f"usage_{msg_id}", "data": usage})
    yield _sse({"type": "finish-step"})
    yield _sse({"type": "finish"})
    yield "data: [DONE]\n\n"
