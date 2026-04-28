from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langfuse.langchain import CallbackHandler
from loguru import logger
from sqlmodel import select

from app import tool_registry
from app.config import get_settings
from app.db import async_session
from app.graphs.main_agent import (
    build_agent as build_agent_for_turn,
)
from app.graphs.main_agent import (
    default_subagents,
)
from app.llm import context_max_tokens, resolve_llm
from app.models import SkillFlag, ToolFlag
from app.schemas.chat import ChatRequest
from app.skills_registry import discover_skills, filter_enabled
from app.streaming import stream_chat
from app.tasks.runner import persist_run_messages, persist_task_run_checkpoint, run_task
from app.tasks.storage import get_task

router = APIRouter()


async def _flags() -> dict[str, bool]:
    async with async_session() as s:
        rows = (await s.execute(select(ToolFlag))).scalars().all()
    return {r.name: r.enabled for r in rows}


async def _skill_flags() -> dict[str, bool]:
    async with async_session() as s:
        rows = (await s.execute(select(SkillFlag))).scalars().all()
    return {r.name: r.enabled for r in rows}


async def _enabled_skills():
    flags = await _skill_flags()
    return filter_enabled(discover_skills(get_settings().skills_dir), flags)


_STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    state = request.app.state
    llm = resolve_llm(state, req.model)
    logger.info(
        f"/chat thread={req.id} reset={req.reset} msgs={len(req.messages)} "
        f"model={req.model} task_run={bool(req.task_run)}"
    )
    if req.reset:
        await state.checkpointer.adelete_thread(req.id)

    if req.task_run is not None:
        task = await get_task(req.task_run.task_id)
        if task is None:
            raise HTTPException(404, f"task {req.task_run.task_id} not found")
        await persist_run_messages(session_id=req.id, task=task, variables=req.task_run.variables)
        lc: list = []

        async def _stream_then_persist():
            async for evt in run_task(
                task,
                req.task_run.variables,
                state=state,
                session_id=req.id,
                llm=llm,
                lc_messages=lc,
            ):
                yield evt
            await persist_task_run_checkpoint(state.checkpointer, req.id, lc)

        return StreamingResponse(
            _stream_then_persist(),
            media_type="text/event-stream",
            headers=_STREAM_HEADERS,
        )
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
    enabled_skills = await _enabled_skills()
    graph = build_agent_for_turn(
        llm=llm,
        tools=tools,
        checkpointer=state.checkpointer,
        subagents=subagents,
        enabled_skills=enabled_skills,
    )
    logger.debug(f"agent built thread={req.id} subagents={[s.get('name') for s in subagents]}")
    ctx_max = context_max_tokens(llm)
    langfuse_handler = CallbackHandler() if get_settings().langfuse_secret_key else None
    if req.resume is not None:
        # tool_call_id is informational — LangGraph resumes by config/thread,
        # not by tool_call_id — but we log it so a stuck thread can be traced
        # back to which pending quiz the user answered.
        logger.info(
            f"resume thread={req.id} tool_call_id={req.resume.tool_call_id!r} "
            f"value_preview={req.resume.value[:80]!r}"
        )
        return StreamingResponse(
            stream_chat(
                graph=graph,
                thread_id=req.id,
                lc_messages=[],
                session_id=req.id,
                resume_value=req.resume.value,
                context_max_tokens=ctx_max,
                model_id=req.model,
                checkpointer=state.checkpointer,
                langfuse_handler=langfuse_handler,
            ),
            media_type="text/event-stream",
            headers=_STREAM_HEADERS,
        )
    lc_messages = await req.to_lc_messages(last_only=not req.reset)
    return StreamingResponse(
        stream_chat(
            graph=graph,
            thread_id=req.id,
            lc_messages=lc_messages,
            session_id=req.id,
            context_max_tokens=ctx_max,
            model_id=req.model,
            langfuse_handler=langfuse_handler,
        ),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )
