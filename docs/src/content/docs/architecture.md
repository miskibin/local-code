---
title: Architecture map
description: Where things live and what owns what.
---

## Where to look

| Module       | Path                                | Owns                                                   |
| ------------ | ----------------------------------- | ------------------------------------------------------ |
| Core         | `backend/app/main.py` + `app.state` | Lifespan, app-scoped singletons.                       |
| Commands     | `backend/app/commands/`             | Slash commands, dispatch.                              |
| Tools        | `backend/app/tools/`                | Auto-discovered LangChain tools.                       |
| MCPs         | `backend/app/mcp_registry.py`       | Hot-reloadable MCP servers.                            |
| Streaming    | `backend/app/streaming.py`          | AI SDK UI parts; subagent nesting.                     |
| Persistence  | `backend/app/db.py`, `models.py`    | `app.db` + LangGraph `checkpoints.db`.                 |
| Frontend     | `frontend/app/`                     | UI, transport, tool render registry.                   |

## Per-turn flow

```mermaid
flowchart LR
    FE[useChat] -- POST /chat --> CHAT[/chat route/]
    CHAT --> Build[build_agent_for_turn]
    Build --> Tools[active tools = local + MCP, filter by ToolFlag]
    Build --> Subs[default_subagents]
    Build --> Agent[deepagents agent]
    Agent --> LLM[Ollama]
    Agent --> Stream[streaming.py SSE]
    Stream --> FE
    Agent --> CK[(checkpoints.db)]
    CHAT --> DB[(app.db)]
```

## Two databases

```mermaid
flowchart LR
    AppDB[(app.db)] -.- A1[ChatSession / ChatMessage]
    AppDB -.- A2[ToolFlag / MCPServerConfig]
    AppDB -.- A3[SavedArtifact]
    CK[(checkpoints.db)] -.- C1[LangGraph thread state]
    Reset[req.reset] -- adelete_thread --> CK
```

`app.db` survives resets. `checkpoints.db` is wiped per-thread when
`req.reset == true`.
