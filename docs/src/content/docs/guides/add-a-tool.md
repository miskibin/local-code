---
title: Add a tool
description: One file in backend/app/tools/.
---

```python
# backend/app/tools/timezone_now.py
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


@tool
def timezone_now(tz: str) -> str:
    """Current ISO 8601 timestamp for an IANA timezone."""
    return datetime.now(ZoneInfo(tz)).isoformat()
```

Restart the backend. Discovery: any module attribute satisfying
`isinstance(_, BaseTool)` is registered. New tools default to enabled.

For a custom UI: [Render a custom tool UI](/guides/render-tool-ui/).

## Don't

- Don't make tools stateful — they're shared across all turns and users.
- Don't wrap calls in try/except for "safety". Let it fail.
- Don't add it to `default_subagents()` unless you actually need a
  subagent.
