from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest
from app.streaming import stream_chat

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    graph = request.app.state.graph
    return StreamingResponse(
        stream_chat(
            graph=graph,
            thread_id=req.id,
            lc_messages=req.to_lc_messages(),
        ),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
