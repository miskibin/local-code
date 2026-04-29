from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from fastapi import Request

from app.models import User


@dataclass
class CommandContext:
    request: Request
    user: User
    session_id: str


@dataclass
class StaticResult:
    text: str


@dataclass
class SubagentResult:
    subagent: dict[str, Any]
    user_message: str
    tool_names: list[str] = field(default_factory=list)


CommandResult = StaticResult | SubagentResult


@runtime_checkable
class Command(Protocol):
    name: str
    description: str
    arg_hint: str

    async def handle(
        self,
        *,
        arg: str,
        ctx: CommandContext,
    ) -> CommandResult: ...
