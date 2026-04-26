from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlmodel import select
from app.schemas.chat import ChatRequest
from app.streaming import stream_chat
from app.db import async_session
from app.models import ToolFlag
from app import tool_registry
from app.graphs.main_agent import build_agent as build_agent_for_turn, default_subagents

router = APIRouter()


async def _flags() -> dict[str, bool]:
    async with async_session() as s:
        rows = (await s.execute(select(ToolFlag))).scalars().all()
    return {r.name: r.enabled for r in rows}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    state = request.app.state
    if req.reset:
        await state.checkpointer.adelete_thread(req.id)
    flags = await _flags()
    mcp_tools = state.mcp_registry.tools if hasattr(state, "mcp_registry") else []
    tools = tool_registry.active_tools(
        tool_registry.discover_tools(),
        mcp_tools,
        flags,
    )
    tools_by_name = {t.name: t for t in tools}
    subagents = []
    for spec in default_subagents():
        resolved = dict(spec)
        if "tools" in resolved:
            resolved["tools"] = [
                tools_by_name[n] for n in resolved["tools"] if n in tools_by_name
            ]
        subagents.append(resolved)
    graph = build_agent_for_turn(
        llm=state.llm,
        tools=tools,
        checkpointer=state.checkpointer,
        subagents=subagents,
    )
    return StreamingResponse(
        stream_chat(graph=graph, thread_id=req.id, lc_messages=req.to_lc_messages()),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
