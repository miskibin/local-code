import logging
import sys
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


NOISY_LOGGERS = (
    "aiosqlite",
    "httpcore",
    "httpcore.http11",
    "httpcore.connection",
    "httpx",
    "urllib3",
    "asyncio",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "uvicorn.access",
    "langchain",
    "langgraph",
    "langchain_ollama",
    "langchain_mcp_adapters",
    "mcp",
)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers = [InterceptHandler()]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "httpx"):
        logging.getLogger(name).handlers = [InterceptHandler()]
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_callbacks() -> list:
    # Langfuse stays disabled per spec. Hook here if/when re-enabled.
    return []
