from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import get_settings
from app.db import init_db
from app.observability import setup_logging
from app.routes.chat import router as chat_router
from app.graphs.main_agent import build_agent, build_ollama_llm
from app.tool_registry import discover_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    await init_db()

    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as saver:
        llm = build_ollama_llm(settings)
        local_tools = discover_tools()
        app.state.local_tools = local_tools
        app.state.mcp_tools = []
        app.state.graph = build_agent(
            llm=llm, tools=local_tools, checkpointer=saver,
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
    return app


app = create_app()
