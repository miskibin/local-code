---
title: Add a tool
description: Drop a new LangChain tool into backend/app/tools/ and have the agent pick it up.
---

You want the agent to be able to call a new function. The minimum
viable change is one Python file.

## 1. Create the tool

Pick a snake-case filename — the file name is irrelevant to the registry
but should describe what the tool does.

```python
# backend/app/tools/timezone_now.py
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


@tool
def timezone_now(tz: str) -> str:
    """Return the current ISO 8601 timestamp for an IANA timezone name."""
    return datetime.now(ZoneInfo(tz)).isoformat()
```

The discovery rule: any **module attribute** whose value `isinstance(_,
BaseTool)` is true is registered. `@tool` produces a `BaseTool`, so an
exported decorated function works.

## 2. Restart the backend

`uv run uvicorn app.main:app --reload` will pick the new tool up. On
boot you'll see a log line like:

```
discovered N local tools: [..., 'timezone_now']
```

## 3. Verify it's active

A tool with no matching `ToolFlag` row defaults to `enabled=True`, so it
should be available to the agent immediately. To toggle it, use the
Settings UI or write a row directly:

```sql
INSERT INTO toolflag(name, enabled) VALUES ('timezone_now', 1)
ON CONFLICT(name) DO UPDATE SET enabled=excluded.enabled;
```

## 4. (Optional) Custom render

If you want a custom UI for this tool's output, see
[Render a custom tool UI](/guides/render-tool-ui/).

## Pitfalls

- **Don't construct stateful tools.** They're shared across all turns and
  users. Tool args carry per-call state.
- **Don't swallow errors.** Let exceptions bubble; the agent will see
  them in the tool result and react. No try/except wrappers "for safety".
- **Don't add the tool to `default_subagents()` unless you actually want
  a subagent.** The main agent already gets the merged set.
