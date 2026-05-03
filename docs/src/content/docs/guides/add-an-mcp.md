---
title: Register an MCP server
description: Add a new MCP server so its tools join the active set.
---

The harness merges MCP tools with local tools every turn. Adding a server
means inserting an `MCPServerConfig` row and triggering a registry sync.

## Two ways

### A. Via the Settings UI (preferred)

The frontend has an MCPs panel that does the right thing:

1. Open Settings → MCPs.
2. Click **Add server**.
3. Fill in `name`, `enabled`, and `connection`. Templates exist for both
   transports.
4. Save. The backend persists the row and calls `MCPRegistry.sync_from_db`
   — the new tools are live immediately, no restart.

### B. Via REST

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-User-Email: you@example.com" \
  -d '{
    "name": "my-server",
    "enabled": true,
    "connection": {
      "transport": "streamable_http",
      "url": "https://example.com/mcp"
    }
  }'
```

`PUT /mcp/{name}` updates, `DELETE /mcp/{name}` removes. All three trigger
a sync.

### C. Seed at startup (only for built-ins)

For a server that should ship with the app, add an idempotent insert in
`main.lifespan`:

```python
async with async_session() as s:
    if await s.get(MCPServerConfig, "my-server") is None:
        s.add(MCPServerConfig(
            name="my-server",
            enabled=True,
            connection={"transport": "streamable_http", "url": "..."},
        ))
        await s.commit()
```

Don't seed user-specific servers this way.

## Connection shapes

```jsonc
// 1. HTTP streamable
{ "transport": "streamable_http", "url": "https://docs.langchain.com/mcp" }

// 2. stdio process
{ "transport": "stdio", "command": "uvx", "args": ["some-mcp-package"] }
```

## What if it doesn't connect?

Logs will show the failure during sync. The server's tools simply aren't
in `registry.tools` this turn. **Don't** wrap caller code in retries or
fallbacks; surface the registry's actual state. Fix the connection.

## Naming

`name` is the primary key. Choose something short and stable — it's used
in logs and (if you flag specific tools) in `ToolFlag` names.
