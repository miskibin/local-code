from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlmodel import select
from app.config import get_settings
from app.db import init_db, async_session
from app.models import MCPServerConfig
from app.observability import setup_logging
from app.routes.chat import router as chat_router
from app.routes.tools import router as tools_router
from app.routes.mcp import router as mcp_router
from app.routes.sessions import router as sessions_router
from app.graphs.main_agent import build_ollama_llm
from app.mcp_registry import MCPRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    await init_db()

    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as saver:
        app.state.llm = build_ollama_llm(settings)
        app.state.checkpointer = saver
        app.state.mcp_registry = MCPRegistry()
        async with async_session() as s:
            cfgs = list((await s.execute(select(MCPServerConfig))).scalars().all())
        await app.state.mcp_registry.sync_from_db(cfgs)
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
    return app


app = create_app()
