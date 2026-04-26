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


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers = [InterceptHandler()]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "httpx"):
        logging.getLogger(name).handlers = [InterceptHandler()]


def get_callbacks() -> list:
    # Langfuse stays disabled per spec. Hook here if/when re-enabled.
    return []
