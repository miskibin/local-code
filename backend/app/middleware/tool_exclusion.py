"""Tool-exclusion middleware (vendored from deepagents).

deepagents' built-in `_ToolExclusionMiddleware` is a private symbol; depending
on it directly couples our agent build to deepagents' internal layout. The
implementation is small (filter `request.tools` by name), so we keep our own
copy here and rely only on the public `langchain.agents.middleware.types`
surface.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.tools import BaseTool


def _tool_name(tool: BaseTool | dict[str, Any]) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
        return name if isinstance(name, str) else None
    name = getattr(tool, "name", None)
    return name if isinstance(name, str) else None


class ToolExclusionMiddleware(AgentMiddleware):
    """Strip the named tools from each model request.

    Place late in the middleware stack so middleware-injected tools
    (filesystem, subagent helpers) can also be filtered.
    """

    def __init__(self, *, excluded: frozenset[str]) -> None:
        self._excluded = excluded

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        if self._excluded:
            filtered = [t for t in request.tools if _tool_name(t) not in self._excluded]
            request = request.override(tools=filtered)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        if self._excluded:
            filtered = [t for t in request.tools if _tool_name(t) not in self._excluded]
            request = request.override(tools=filtered)
        return await handler(request)
