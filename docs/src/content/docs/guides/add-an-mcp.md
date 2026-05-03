---
title: Register an MCP server
description: One row in app.db, one registry sync.
---

Easiest path: **Settings → MCPs → Add server** in the UI. The backend
persists the row and triggers `MCPRegistry.sync_from_db` — tools are
live immediately.

Or via REST:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-User-Email: you@example.com" \
  -d '{
    "name": "my-server",
    "enabled": true,
    "connection": {"transport": "streamable_http", "url": "https://example.com/mcp"}
  }'
```

`PUT /mcp/{name}` and `DELETE /mcp/{name}` also re-sync.

## Connection shapes

```jsonc
{ "transport": "streamable_http", "url": "..." }
{ "transport": "stdio", "command": "uvx", "args": ["..."] }
```

## Don't

- Don't seed user-specific servers in `lifespan`. That's for built-ins
  only.
- If a server fails to connect, **fix it** — don't add caller-side
  retries or fallbacks. Logs show the failure; tools just don't appear
  this turn.
