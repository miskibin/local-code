from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime

from app.skills_registry import SkillInfo

_PROMPT_TEMPLATE = """\
## Skills Library

You have access to long-form playbooks (skills) that contain detailed
instructions for specific tasks. The list below shows each skill's name and
description. When a user request matches a skill, call `read_file` on the
skill's path to load the full instructions before acting.

**Available skills:**
{skills_list}

**Usage:**
1. Match the user's request to a skill description.
2. Load the skill: `read_file(file_path="<path>", limit=1000)`.
3. Follow the skill's instructions exactly.

If no skill matches, proceed normally."""


def _format_list(skills: list[SkillInfo]) -> str:
    return "\n".join(
        f"- **{s.name}**: {s.description}\n  -> Read `{s.path}` for full instructions"
        for s in skills
    )


class StateSkillsMiddleware(AgentMiddleware):
    """Pre-seed `state["files"]` with skill bodies and inject a system-prompt
    block listing available skills.

    Avoids deepagents' SkillsMiddleware backend round-trip: skills are read
    from disk once at agent build time and copied straight into LangGraph
    state, so the agent's `read_file` tool (StateBackend-backed) finds them
    without exposing a real-disk filesystem to the model.
    """

    def __init__(self, *, skills: list[SkillInfo]) -> None:
        self._skills = skills
        self._prompt_block = _PROMPT_TEMPLATE.format(skills_list=_format_list(skills))

    def _state_seed(self) -> dict[str, Any]:
        files = {s.path: {"content": s.body} for s in self._skills}
        metadata = [
            {"name": s.name, "description": s.description, "path": s.path} for s in self._skills
        ]
        return {"files": files, "skills_metadata": metadata}

    def before_agent(self, state: Any, runtime: Runtime) -> dict[str, Any] | None:
        return self._state_seed()

    async def abefore_agent(self, state: Any, runtime: Runtime) -> dict[str, Any] | None:
        return self._state_seed()

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        new_system = append_to_system_message(request.system_message, self._prompt_block)
        return handler(request.override(system_message=new_system))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        new_system = append_to_system_message(request.system_message, self._prompt_block)
        return await handler(request.override(system_message=new_system))
