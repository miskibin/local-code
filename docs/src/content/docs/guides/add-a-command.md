---
title: Add a slash command
description: One file in backend/app/commands/.
---

```python
# backend/app/commands/echo.py
from app.commands.base import Command, CommandContext, StaticResult


class EchoCommand:
    name = "echo"
    description = "Echo the argument back."
    arg_hint = "<text>"

    async def handle(self, *, arg: str, ctx: CommandContext) -> StaticResult:
        return StaticResult(text=arg or "(nothing to echo)")


echo = EchoCommand()   # registry only sees module-scope instances
```

Restart. The user can now type `/echo something`.

## Result types

- `StaticResult(text=...)` — assistant text, streamed as-is.
- `SubagentResult(subagent={...}, user_message=..., tool_names=[...])` —
  delegate to a subagent with a curated tool list. Tool names are
  resolved against the live registry per turn.

## Don't

- Don't name the file `base.py` / `dispatcher.py` / `registry.py` — the
  registry skips those.
- Don't catch arg-parsing errors inside `handle`; let them surface.
