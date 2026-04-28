"""Tool-exclusion middleware (vendored from deepagents, extended).

Two responsibilities:

1. ``wrap_model_call`` — strip excluded tools from ``request.tools`` so the
   model is never *bound* to them. Same logic as deepagents' private
   ``_ToolExclusionMiddleware``.

2. ``wrap_tool_call`` — refuse execution if an excluded tool name reaches
   the ``ToolNode`` anyway. Required because ``create_agent`` registers
   *every* middleware-injected tool in the ``ToolNode`` regardless of what
   ``bind_tools`` saw. Small models (gemma) routinely emit tool calls for
   names they were never bound to (recalled from training prior), and the
   ``ToolNode`` happily executes them. Filtering only at bind time leaves
   that hallucination path open.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command


def _tool_name(tool: BaseTool | dict[str, Any]) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
        return name if isinstance(name, str) else None
    name = getattr(tool, "name", None)
    return name if isinstance(name, str) else None


_REFUSAL_TEMPLATE = (
    "Tool `{name}` is not available in this agent. Do not call it again. "
    "Pick a different tool from the bound list or answer without tools."
)


class ToolExclusionMiddleware(AgentMiddleware):
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

    def _refusal(self, request: ToolCallRequest) -> ToolMessage:
        call = request.tool_call
        return ToolMessage(
            content=_REFUSAL_TEMPLATE.format(name=call.get("name", "?")),
            tool_call_id=call.get("id", ""),
            name=call.get("name"),
            status="error",
        )

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        name = (request.tool_call or {}).get("name")
        if name in self._excluded:
            return self._refusal(request)
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        name = (request.tool_call or {}).get("name")
        if name in self._excluded:
            return self._refusal(request)
        return await handler(request)
