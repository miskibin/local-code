from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlmodel import select

from app import tool_registry
from app.config import get_settings
from app.db import async_session
from app.graphs.main_agent import (
    build_agent as build_agent_for_turn,
)
from app.graphs.main_agent import (
    build_gemini_llm,
    build_ollama_llm,
    default_subagents,
)
from app.models import ToolFlag
from app.schemas.chat import ChatRequest
from app.streaming import stream_chat

router = APIRouter()


async def _flags() -> dict[str, bool]:
    async with async_session() as s:
        rows = (await s.execute(select(ToolFlag))).scalars().all()
    return {r.name: r.enabled for r in rows}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    state = request.app.state
    llm = state.llm_cache.get(req.model)
    if llm is None:
        settings = get_settings()
        if req.model.startswith("gemini"):
            llm = build_gemini_llm(settings, model=req.model)
        else:
            llm = build_ollama_llm(settings, model=req.model)
        state.llm_cache[req.model] = llm
    logger.info(
        f"/chat thread={req.id} reset={req.reset} msgs={len(req.messages)} model={req.model}"
    )
    if req.reset:
        await state.checkpointer.adelete_thread(req.id)
    flags = await _flags()
    mcp_tools = state.mcp_registry.tools if hasattr(state, "mcp_registry") else []
    tools = tool_registry.active_tools(
        tool_registry.discover_tools(),
        mcp_tools,
        flags,
    )
    logger.debug(
        f"tools active={len(tools)} (local+mcp post-filter, names={[t.name for t in tools]})"
    )
    tools_by_name = {t.name: t for t in tools}
    subagents = []
    for spec in default_subagents():
        resolved = dict(spec)
        if "tools" in resolved:
            resolved["tools"] = [tools_by_name[n] for n in resolved["tools"] if n in tools_by_name]
        subagents.append(resolved)
    graph = build_agent_for_turn(
        llm=llm,
        tools=tools,
        checkpointer=state.checkpointer,
        subagents=subagents,
    )
    logger.debug(f"agent built thread={req.id} subagents={[s.get('name') for s in subagents]}")
    return StreamingResponse(
        stream_chat(
            graph=graph,
            thread_id=req.id,
            lc_messages=req.to_lc_messages(),
            session_id=req.id,
        ),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
