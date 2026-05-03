---
title: Add a slash command
description: Wire up a new /command that the user can invoke in chat.
---

Slash commands are anything triggered by a leading `/` in a user message:
`/feedback`, `/remember`, etc. Adding one is a single file in
`backend/app/commands/`.

## 1. Implement the `Command` protocol

```python
# backend/app/commands/echo.py
from app.commands.base import Command, CommandContext, StaticResult


class EchoCommand:
    name = "echo"
    description = "Echo the argument back."
    arg_hint = "<text>"

    async def handle(self, *, arg: str, ctx: CommandContext) -> StaticResult:
        return StaticResult(text=arg or "(nothing to echo)")


echo = EchoCommand()        # the registry only sees module attributes
```

`discover_commands()` skips classes and only registers **instances** that
satisfy the `Command` protocol — so make sure you instantiate it at module
scope.

## 2. Pick a result type

| Result type        | Use it when                                                            |
| ------------------ | ---------------------------------------------------------------------- |
| `StaticResult`     | You already have the assistant's reply as plain text.                  |
| `SubagentResult`   | You want to delegate to a subagent with a curated toolset.             |

`SubagentResult` shape:

```python
SubagentResult(
    subagent={"name": "echo-agent", "description": "...", "prompt": "..."},
    user_message="user-facing rewrite of the request",
    tool_names=["sql_query", "web_fetch"],   # resolved against the live registry
)
```

## 3. Restart the backend

On boot you'll see:

```
discovered N slash commands: [..., 'echo']
```

The command is now callable as `/echo something`.

## Naming

`name` is what the user types after the slash and what shows up in the
slash-command picker. Keep it short, lowercase, no whitespace.

## Pitfalls

- Don't import `dispatcher`, `registry`, or `base` as your command name —
  the registry skips those module names.
- Don't catch user-input parsing errors inside `handle`; let them surface.
