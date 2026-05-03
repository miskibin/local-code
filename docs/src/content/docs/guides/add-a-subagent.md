---
title: Add a subagent
description: A specialized worker callable via the task dispatcher.
---

Subagents live in `default_subagents()` in
`backend/app/graphs/main_agent.py`. Use one when you want a **focused
prompt and a curated toolset** for a sub-task.

If you only need a new function, [add a tool](/guides/add-a-tool/).
If you need user-triggered, [add a command](/guides/add-a-command/).

```python
def default_subagents() -> list[dict]:
    return [
        sql_subagent(),
        {
            "name": "translator",
            "description": "Translates strings between languages.",
            "prompt": TRANSLATOR_PROMPT,
            "tools": ["web_fetch"],   # names; resolved against live registry
        },
    ]
```

`tools` is a list of **names**. A subagent only sees a tool if it's in
the active set this turn (i.e. enabled in `ToolFlag` and present in the
local/MCP merge).

## Don't

- Subagent LLM tokens **don't** reach top-level text. They render inside
  the dispatcher tool's result. See [Streaming](/modules/streaming/).
- Don't open another checkpointer; the subagent shares the app's.
