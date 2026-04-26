from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger
from sqlmodel import select

from app.config import get_settings
from app.db import async_session, init_db
from app.mcp_registry import MCPRegistry
from app.models import MCPServerConfig
from app.observability import setup_logging
from app.routes.artifacts import router as artifacts_router
from app.routes.chat import router as chat_router
from app.routes.mcp import router as mcp_router
from app.routes.sessions import router as sessions_router
from app.routes.tools import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        f"log_level={settings.log_level} base_url={settings.ollama_base_url}"
    )
    await init_db()

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
        yield


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

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(chat_router)
    app.include_router(tools_router)
    app.include_router(mcp_router)
    app.include_router(sessions_router)
    app.include_router(artifacts_router)
    return app


app = create_app()
