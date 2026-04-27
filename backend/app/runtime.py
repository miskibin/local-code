"""Process-wide singletons set at FastAPI startup so request-time code (tools,
helpers) can reach them without threading them through every signature."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_sandbox import PyodideSandbox

_sandbox: PyodideSandbox | None = None


def set_sandbox(sandbox: PyodideSandbox) -> None:
    global _sandbox  # noqa: PLW0603 -- module-level singleton, set once in lifespan
    _sandbox = sandbox


def get_sandbox() -> PyodideSandbox:
    if _sandbox is None:
        raise RuntimeError("python sandbox not initialized; lifespan did not run")
    return _sandbox
