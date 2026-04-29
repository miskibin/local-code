from dataclasses import dataclass

from app.commands.base import CommandContext, StaticResult
from app.db import async_session
from app.models import UserInstructions
from app.utils import now_utc

MAX_LINES = 50


def _count_lines(content: str) -> int:
    return sum(1 for line in content.split("\n") if line.strip())


@dataclass
class RememberCommand:
    name: str = "remember"
    description: str = "Append a line to your custom instructions for the agent."
    arg_hint: str = "<what to remember>"

    async def handle(self, *, arg: str, ctx: CommandContext) -> StaticResult:
        line = arg.strip()
        if not line:
            return StaticResult(
                text=("`/remember` needs some text. Example: `/remember always reply in Polish`.")
            )
        async with async_session() as s:
            row = await s.get(UserInstructions, ctx.user.id)
            existing_count = _count_lines(row.content) if row else 0
            if existing_count >= MAX_LINES:
                return StaticResult(
                    text=(
                        f"You already have {existing_count} remembered notes "
                        f"(limit: {MAX_LINES}). Edit them in Settings → Instructions to make room."
                    )
                )
            if row is None:
                row = UserInstructions(
                    user_id=ctx.user.id, content=f"- {line}", updated_at=now_utc()
                )
                s.add(row)
            else:
                base = row.content.rstrip()
                row.content = f"{base}\n- {line}" if base else f"- {line}"
                row.updated_at = now_utc()
            await s.commit()
        return StaticResult(text=f"Remembered: {line}")


command = RememberCommand()
