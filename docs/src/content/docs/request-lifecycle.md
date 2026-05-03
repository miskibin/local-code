---
title: How a turn works
description: From "user hits Enter" to the SSE bytes.
---

```mermaid
sequenceDiagram
    autonumber
    participant FE as ChatView
    participant API as /chat
    participant BL as build_agent_for_turn
    participant AG as agent
    participant CP as checkpoints.db

    FE->>API: POST {id, messages, reset}
    API->>BL: read flags + MCPs
    BL-->>API: agent (live tool set)
    API->>AG: astream_events(thread_id=session.id)
    loop per event
      AG-->>FE: text / tool / data SSE part
    end
    AG->>CP: persist checkpoint
```

The agent is rebuilt every turn because `ToolFlag` and `MCPServerConfig`
can change between turns (Settings UI, `/mcp` endpoints). We read both
fresh and pass them to `build_agent_for_turn`.

## Reset

`req.reset == true` calls `state.checkpointer.adelete_thread(req.id)`.
LangGraph thread state goes; persisted `ChatMessage` rows in `app.db`
stay.

## Subagents

The dispatcher tool is `task`. When it fires, inner tool events get
`providerMetadata.subagent.parentToolCallId` so the frontend can group
them under their parent. Inner LLM tokens are **not** forwarded as
top-level text — they stay inside the tool result. See
[Streaming](/modules/streaming/).
