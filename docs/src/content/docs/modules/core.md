---
title: Core
description: Lifespan and per-turn agent build.
---

```mermaid
flowchart LR
    Start[lifespan] --> S1[llm_cache]
    Start --> S2[checkpointer AsyncSqliteSaver]
    Start --> S3[mcp_registry]
    Start --> S4[commands]
    Turn[/chat turn] --> Read[read DB: flags + MCPs]
    Read --> Build[build_agent_for_turn]
```

App-scoped singletons live on `app.state`. Per-turn data (tool flags,
MCP configs, user instructions) is read fresh in the `/chat` route.

## Why rebuild every turn

`ToolFlag` and `MCPServerConfig` are mutable from the UI. A cached agent
would serve a stale toolset. `build_agent_for_turn` re-reads the
registries, calls `default_subagents()`, and hands everything to
`deepagents.create_deep_agent`. Cheap — only the graph is rebuilt; the
LLM client and checkpointer are reused.

## Don't put per-turn state on `app.state`

If a value can change between turns or per user, read it inside the
route. `app.state` is **only** for true app-scoped singletons.
