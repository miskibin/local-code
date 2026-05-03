---
title: Add a subagent
description: Give the main agent a specialized worker callable via the task tool.
---

Subagents are defined in `default_subagents()` in
`backend/app/graphs/main_agent.py`. The main agent reaches them through
the built-in `task` dispatcher tool.

## When to add one

Add a subagent when you want **a curated toolset and a focused system
prompt** for a sub-task — e.g. the SQL agent has only the SQL tools and a
prompt that bakes in the schema.

If you just need a new tool, [add a tool](/guides/add-a-tool/). If you
need a user-triggered command, [add a command](/guides/add-a-command/).

## Shape of a subagent entry

```python
{
    "name": "translator",
    "description": "Translates strings between languages.",
    "prompt": "You are a precise translator. ...",
    "tools": ["web_fetch"],   # resolved by name against the live registry
}
```

`tools` is a list of **names**. Resolution against the active registry
happens inside `build_agent_for_turn` — so a subagent only sees a tool if
it's in the active set this turn.

## Plug it into `default_subagents`

```python
def default_subagents() -> list[dict]:
    return [
        sql_subagent(),
        # ...
        {
            "name": "translator",
            "description": "Translates strings between languages.",
            "prompt": TRANSLATOR_PROMPT,
            "tools": ["web_fetch"],
        },
    ]
```

## Caveats

- Subagent LLM tokens **aren't** forwarded as top-level text — they stay
  inside the dispatcher tool's result. See [Streaming](/modules/streaming/).
- A subagent inherits the same checkpointer; don't open another one.
- If you find yourself duplicating prompt scaffolding across subagents,
  factor it into a small helper in the same module — but only after
  there's actual duplication. Don't preemptively abstract.
