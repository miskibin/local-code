import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langfuse import get_client
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger
from sqlmodel import select

from app.config import get_settings

_settings_for_env = get_settings()
if _settings_for_env.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_SECRET_KEY", _settings_for_env.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", _settings_for_env.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", _settings_for_env.langfuse_base_url)
from app.db import async_session, init_db  # noqa: E402
from app.mcp_registry import MCPRegistry  # noqa: E402
from app.models import MCPServerConfig  # noqa: E402
from app.observability import setup_logging  # noqa: E402
from app.routes.artifacts import router as artifacts_router  # noqa: E402
from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.chat import router as chat_router  # noqa: E402
from app.routes.feedback import router as feedback_router  # noqa: E402
from app.routes.mcp import router as mcp_router  # noqa: E402
from app.routes.sessions import router as sessions_router  # noqa: E402
from app.routes.skills import router as skills_router  # noqa: E402
from app.routes.tasks import router as tasks_router  # noqa: E402
from app.routes.tools import router as tools_router  # noqa: E402
from app.routes.user_instructions import router as user_instructions_router  # noqa: E402
from app.tools.sql_subagent_query import schema_blob  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(f"log_level={settings.log_level} base_url={settings.ollama_base_url}")
    await init_db()
    # Seed built-in MCP servers on first run (idempotent).
    _langchain_docs_connection = {
        "transport": "streamable_http",
        "url": "https://docs.langchain.com/mcp",
    }
    _broken_stdio = {"transport": "stdio", "command": "uvx", "args": ["langchain-docs-mcp"]}
    async with async_session() as s:
        existing = await s.get(MCPServerConfig, "langchain-docs")
        if existing is None:
            s.add(
                MCPServerConfig(
                    name="langchain-docs", enabled=True, connection=_langchain_docs_connection
                )
            )
            await s.commit()
        elif existing.connection == _broken_stdio:
            existing.connection = _langchain_docs_connection
            s.add(existing)
            await s.commit()
    # Warm the cached Chinook schema off the request path; default_subagents()
    # bakes it into the sql-agent system prompt and is called per /chat turn.
    schema_blob()

    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as saver:
        app.state.llm_cache = {}
        app.state.checkpointer = saver
        app.state.mcp_registry = MCPRegistry()
        async with async_session() as s:
            cfgs = list((await s.execute(select(MCPServerConfig))).scalars().all())
        await app.state.mcp_registry.sync_from_db(cfgs)
        n_tools = len(app.state.mcp_registry.tools)
        logger.info(
            f"startup ready: {len(cfgs)} mcp servers configured, {n_tools} mcp tools loaded"
        )
        try:
            yield
        finally:
            if settings.langfuse_secret_key:
                get_client().flush()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(lifespan=lifespan, title="Local Gemma 4 Agentic Harness")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _unhandled_exc(request: Request, exc: Exception):
        # Return JSON so the response goes through CORSMiddleware (Starlette's
        # default ServerErrorMiddleware emits a plain-text 500 outside CORS,
        # which the browser surfaces only as "Failed to fetch").
        logger.exception(f"unhandled {request.method} {request.url.path}: {exc!r}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            },
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(tools_router)
    app.include_router(mcp_router)
    app.include_router(sessions_router)
    app.include_router(artifacts_router)
    app.include_router(tasks_router)
    app.include_router(skills_router)
    app.include_router(feedback_router)
    app.include_router(user_instructions_router)
    return app


app = create_app()
