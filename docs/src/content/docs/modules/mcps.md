---
title: MCPs
description: How MCP servers are configured, loaded, hot-reloaded, and merged with local tools.
---

The harness can talk to **MCP** (Model Context Protocol) servers and
expose their tools to the agent alongside local tools.

## Pieces

| File                              | Role                                                  |
| --------------------------------- | ----------------------------------------------------- |
| `backend/app/mcp_registry.py`     | `MCPRegistry` — connects, caches, merges tools.       |
| `backend/app/models.py`           | `MCPServerConfig` SQLModel row.                       |
| `backend/app/routes/mcp.py`       | REST: list / create / update / delete + hot-reload.   |
| `backend/app/main.py` (lifespan)  | Initial `sync_from_db(cfgs)`.                         |

## Config shape

A `MCPServerConfig` row has `name`, `enabled`, and a `connection` JSON
blob. Two transports are supported:

```jsonc
// streamable_http
{ "transport": "streamable_http", "url": "https://docs.langchain.com/mcp" }

// stdio
{ "transport": "stdio", "command": "uvx", "args": ["some-mcp-package"] }
```

## Lifecycle

```mermaid
flowchart LR
    L[lifespan] --> S0[load all MCPServerConfig from app.db]
    S0 --> R[MCPRegistry.sync_from_db]
    R --> P[per server: connect + cache tools]
    UI[Settings UI] -->|POST/PUT/DELETE /mcp| API[routes/mcp.py]
    API --> S1[update app.db]
    S1 --> R2[registry.sync_from_db again]
    R2 --> Hot[(hot-reload — no restart)]
    Turn[/chat turn] --> Read[read registry.tools]
    Read --> Active[active_tools merge]
```

The registry exposes a flat `tools: list[BaseTool]` so it slots straight
into `active_tools`. Toggling `enabled` toggles whether the server's tools
appear in the merge.

## Built-in seed

`lifespan` seeds a `langchain-docs` MCP server on first run:

```python
{ "transport": "streamable_http", "url": "https://docs.langchain.com/mcp" }
```

If a previous version had a broken stdio connection (`uvx
langchain-docs-mcp`), the lifespan auto-fixes it to the current
`streamable_http` form.

## Failure mode

Connecting to an MCP server can fail (network, bad command, etc.). The
registry logs and skips that server — its tools simply don't appear in the
active set this turn. **Don't add retry loops or graceful fallback in
caller code**; surface the registry's state as-is.

## See also

- [Add an MCP server](/guides/add-an-mcp/) — recipe.
- [Tools](/modules/tools/) — how the merged set reaches the agent.
