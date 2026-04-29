from contextlib import AsyncExitStack

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langfuse.langchain import CallbackHandler
from loguru import logger
from sqlmodel import select

from app import tool_registry
from app.auth import CurrentUser
from app.commands import (
    CommandContext,
    StaticResult,
    SubagentResult,
    parse_slash,
)
from app.commands.stream_static import stream_static_text
from app.config import get_settings
from app.db import async_session
from app.graphs.main_agent import (
    build_agent as build_agent_for_turn,
)
from app.graphs.main_agent import (
    default_subagents,
)
from app.integrations.feedback_context import FeedbackRequestCtx, set_feedback_ctx
from app.llm import context_max_tokens, resolve_llm
from app.models import MCPServerUserFlag, SkillFlag, ToolFlag, UserInstructions
from app.schemas.chat import ChatRequest, TextPart
from app.skills_registry import discover_skills, filter_enabled
from app.streaming import stream_chat
from app.tasks.runner import persist_run_messages, persist_task_run_checkpoint, run_task
from app.tasks.storage import get_task

router = APIRouter()


async def _load_tool_flags(user_id: str) -> dict[str, bool]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(ToolFlag).where(ToolFlag.user_id == user_id))).scalars().all()
        )
        return {r.name: r.enabled for r in rows}


async def _load_skill_flags(user_id: str) -> dict[str, bool]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(SkillFlag).where(SkillFlag.user_id == user_id))).scalars().all()
        )
        return {r.name: r.enabled for r in rows}


async def _load_mcp_user_flags(user_id: str) -> dict[str, bool]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(MCPServerUserFlag).where(MCPServerUserFlag.user_id == user_id)))
            .scalars()
            .all()
        )
        return {r.name: r.enabled for r in rows}


async def _enabled_skills(user_id: str):
    flags = await _load_skill_flags(user_id)
    return filter_enabled(discover_skills(get_settings().skills_dir), flags)


def _filter_mcp_tools(
    mcp_tools,
    tools_by_server: dict[str, list[str]],
    user_flags: dict[str, bool],
):
    disabled_names: set[str] = set()
    for server_name, names in tools_by_server.items():
        if not user_flags.get(server_name, True):
            disabled_names.update(names)
    return [t for t in mcp_tools if t.name not in disabled_names]


_STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


@router.post("/chat")
async def chat(  # noqa: PLR0915 -- request handler; branches on task_run/resume/normal
    req: ChatRequest, request: Request, user: CurrentUser
):
    state = request.app.state
    llm = resolve_llm(state, req.model)
    logger.info(
        f"/chat thread={req.id} user={user.email} reset={req.reset} msgs={len(req.messages)} "
        f"model={req.model} task_run={bool(req.task_run)}"
    )
    if req.reset:
        await state.checkpointer.adelete_thread(req.id)

    if req.task_run is not None:
        task = await get_task(req.task_run.task_id)
        if task is None:
            raise HTTPException(404, f"task {req.task_run.task_id} not found")
        await persist_run_messages(
            session_id=req.id,
            owner_id=user.id,
            task=task,
            variables=req.task_run.variables,
        )
        lc: list = []

        async def _stream_then_persist():
            # Use try/finally so a client disconnect mid-stream still persists
            # the partial transcript — otherwise the run history silently drops
            # on connection loss. `pin_for_stream` blocks any concurrent
            # `/mcp` hot-reload from tearing down sessions a tool inside
            # run_task is still using.
            try:
                async with AsyncExitStack() as stack:
                    registry = getattr(state, "mcp_registry", None)
                    if registry is not None and hasattr(registry, "pin_for_stream"):
                        await stack.enter_async_context(registry.pin_for_stream())
                    async for evt in run_task(
                        task,
                        req.task_run.variables,
                        state=state,
                        session_id=req.id,
                        owner_id=user.id,
                        llm=llm,
                        lc_messages=lc,
                    ):
                        yield evt
            finally:
                if lc:
                    await persist_task_run_checkpoint(state.checkpointer, req.id, lc)

        return StreamingResponse(
            _stream_then_persist(),
            media_type="text/event-stream",
            headers=_STREAM_HEADERS,
        )
    extra_subagent: dict | None = None
    if req.resume is None and req.task_run is None and req.messages:
        last = req.messages[-1]
        last_text = "".join(p.text for p in last.parts if isinstance(p, TextPart))
        parsed = parse_slash(last_text) if last.role == "user" else None
        if parsed is not None:
            name, arg = parsed
            cmd = (state.commands or {}).get(name)
            cmd_ctx = CommandContext(request=request, user=user, session_id=req.id)
            if cmd is None:
                return StreamingResponse(
                    stream_static_text(f"Unknown command: `/{name}`", model_id=req.model),
                    media_type="text/event-stream",
                    headers=_STREAM_HEADERS,
                )
            result = await cmd.handle(arg=arg, ctx=cmd_ctx)
            if isinstance(result, StaticResult):
                return StreamingResponse(
                    stream_static_text(result.text, model_id=req.model),
                    media_type="text/event-stream",
                    headers=_STREAM_HEADERS,
                )
            if isinstance(result, SubagentResult):
                last.parts = [TextPart(type="text", text=result.user_message)]
                extra_subagent = result.subagent

    tool_flags = await _load_tool_flags(user.id)
    mcp_user_flags = await _load_mcp_user_flags(user.id)
    enabled_skills = await _enabled_skills(user.id)
    async with async_session() as s:
        ui = await s.get(UserInstructions, user.id)
    custom_instructions = ui.content if ui else ""
    ctx_max = context_max_tokens(llm)
    langfuse_handler = CallbackHandler() if get_settings().langfuse_secret_key else None
    lc_messages = (
        [] if req.resume is not None else await req.to_lc_messages(last_only=not req.reset)
    )
    user_agent = request.headers.get("user-agent", "")
    request_id = request.headers.get("x-request-id")
    configurable_extras = {
        "reporter_email": user.email,
        "app_version": getattr(state, "app_version", ""),
        "git_sha": getattr(state, "git_sha", ""),
    }
    if req.resume is not None:
        # tool_call_id is informational — LangGraph resumes by config/thread,
        # not by tool_call_id — but we log it so a stuck thread can be traced
        # back to which pending quiz the user answered.
        logger.info(
            f"resume thread={req.id} tool_call_id={req.resume.tool_call_id!r} "
            f"value_preview={req.resume.value[:80]!r}"
        )

    async def _chat_stream():
        set_feedback_ctx(
            FeedbackRequestCtx(
                user_agent=user_agent,
                request_id=request_id,
                langfuse_handler=langfuse_handler,
            )
        )
        # Pin MCP tools for the duration of the stream so a concurrent
        # `/mcp` hot-reload cannot close sessions the agent is mid-call on.
        async with AsyncExitStack() as stack:
            registry = getattr(state, "mcp_registry", None)
            if registry is not None and hasattr(registry, "pin_for_stream"):
                mcp_pinned = await stack.enter_async_context(registry.pin_for_stream())
                tools_by_server = registry.tools_by_server
            elif registry is not None:
                mcp_pinned = list(getattr(registry, "tools", []))
                tools_by_server = getattr(registry, "tools_by_server", {})
            else:
                mcp_pinned = []
                tools_by_server = {}
            mcp_tools = _filter_mcp_tools(mcp_pinned, tools_by_server, mcp_user_flags)
            tools = tool_registry.active_tools(
                tool_registry.discover_tools(),
                mcp_tools,
                tool_flags,
            )
            logger.debug(
                f"tools active={len(tools)} (local+mcp post-filter, "
                f"names={[t.name for t in tools]})"
            )
            tools_by_name = {t.name: t for t in tools}
            subagent_specs = list(default_subagents())
            if extra_subagent is not None:
                subagent_specs.append(extra_subagent)
            subagents = []
            for spec in subagent_specs:
                resolved = dict(spec)
                if "tools" in resolved:
                    resolved["tools"] = [
                        tools_by_name[n] for n in resolved["tools"] if n in tools_by_name
                    ]
                subagents.append(resolved)
            graph = build_agent_for_turn(
                llm=llm,
                tools=tools,
                checkpointer=state.checkpointer,
                subagents=subagents,
                enabled_skills=enabled_skills,
                custom_instructions=custom_instructions,
            )
            logger.debug(
                f"agent built thread={req.id} subagents={[s.get('name') for s in subagents]}"
            )
            async for evt in stream_chat(
                graph=graph,
                thread_id=req.id,
                lc_messages=lc_messages,
                owner_id=user.id,
                session_id=req.id,
                resume_value=req.resume.value if req.resume is not None else None,
                context_max_tokens=ctx_max,
                model_id=req.model,
                checkpointer=state.checkpointer,
                langfuse_handler=langfuse_handler,
                configurable_extras=configurable_extras,
            ):
                yield evt

    return StreamingResponse(
        _chat_stream(),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )
