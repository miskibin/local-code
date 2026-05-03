---
title: Core
description: Lifespan, app.state singletons, and the per-turn agent build.
---

The "core" is the small set of files that wire everything together:

| File                              | Role                                                                  |
| --------------------------------- | --------------------------------------------------------------------- |
| `backend/app/main.py`             | `create_app`, `lifespan`, router includes, exception handler.         |
| `backend/app/config.py`           | `pydantic-settings`; loads `.env`.                                    |
| `backend/app/llm.py`              | LLM client cache (key into `app.state.llm_cache`).                    |
| `backend/app/observability.py`    | `loguru` setup.                                                       |
| `backend/app/auth.py`             | Resolves `X-User-Email` to a `User` row.                              |
| `backend/app/graphs/main_agent.py`| `build_agent_for_turn`, `default_subagents`.                          |
| `backend/app/graphs/state.py`     | LangGraph state schema.                                               |

## What lives on `app.state`

These survive across turns, are created once in `lifespan`, and are read
every request:

```mermaid
flowchart LR
    Lifespan[lifespan startup] --> S1[llm_cache: dict]
    Lifespan --> S2[checkpointer: AsyncSqliteSaver]
    Lifespan --> S3[mcp_registry: MCPRegistry]
    Lifespan --> S4[commands: dict[name, Command]]
    Lifespan --> S5[app_version, git_sha]
    Lifespan -. async with .-> CK[(checkpoints.db)]
```

Anything that depends on per-turn DB state (tool flags, MCP server configs,
user instructions) is **not** on `app.state` — it's read fresh inside
`/chat`.

## Lifespan, in order

1. Load settings, configure logging, set Langfuse env if keys present.
2. `init_db()` — runs SQLModel metadata, applies any seed inserts.
3. Seed built-in MCP servers (e.g. `langchain-docs`) idempotently.
4. Warm `schema_blob()` so the SQL subagent prompt isn't built on the hot
   path.
5. Open `AsyncSqliteSaver` as a context manager (must stay open for the app
   lifetime).
6. Initialize `MCPRegistry` and call `sync_from_db(cfgs)`.
7. `discover_commands()` and store the dict on `app.state`.
8. Hand off to FastAPI, then on shutdown flush Langfuse if configured.

## Why the agent is rebuilt every turn

`ToolFlag` and `MCPServerConfig` are mutable from the UI. If we cached the
agent we'd serve a stale toolset. Instead `routes/chat.py` calls
`build_agent_for_turn(user, session, flags, mcps)` per request, which:

1. Filters merged local + MCP tools through the active flag set.
2. Builds `default_subagents()` and resolves each subagent's `tools` list
   against the live registry.
3. Calls `deepagents.create_deep_agent(...)` with the shared LLM and
   checkpointer.

This is cheap — `deepagents` only assembles a graph; the LLM client and
checkpointer are reused.

## Don't add things to `app.state`

If a value can change between turns (per-user, per-session, DB-backed),
read it inside the route. `app.state` is for **truly app-scoped**
singletons.
