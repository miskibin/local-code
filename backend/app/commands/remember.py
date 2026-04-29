from dataclasses import dataclass

from app.commands.base import CommandContext, StaticResult
from app.db import async_session
from app.models import UserInstructions
from app.utils import now_utc


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
        return StaticResult(text=f"Zapamiętane: {line}")


command = RememberCommand()
