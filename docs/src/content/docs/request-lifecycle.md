---
title: How a turn works
description: From "user hits Enter" to the first SSE byte and back again.
---

A single turn is the unit of work in this app. Understanding it makes every
other module obvious.

## End-to-end sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as ChatView (useChat)
    participant API as /chat route
    participant BL as build_agent_for_turn
    participant AG as deepagents agent
    participant CP as AsyncSqliteSaver
    participant DB as app.db
    participant ST as streaming.py

    U->>FE: types message + Enter
    FE->>API: POST /chat {id, messages, reset}
    API->>DB: load/create ChatSession + persist user msg
    API->>BL: build_agent_for_turn(user, session, flags, mcps)
    BL->>AG: create_deep_agent(llm, tools, subagents, checkpointer=CP)
    API->>AG: astream_events(input, config={thread_id: session.id})
    loop per event
      AG-->>ST: token / tool call / tool result
      ST-->>FE: SSE UI message part
    end
    AG->>CP: persist checkpoint
    API->>DB: persist final assistant message
    API-->>FE: stream end
```

## What `build_agent_for_turn` actually does

```mermaid
flowchart TB
    Start([POST /chat]) --> Flags[load ToolFlag rows]
    Start --> MCP[load MCPServerConfig rows]
    Flags --> Active[active_tools: local + MCP filtered by flags]
    MCP --> Active
    Active --> Subs[default_subagents]
    Subs --> Resolve[resolve subagent.tools names against registry]
    Resolve --> Build[deepagents.create_deep_agent]
    Build --> Run[astream_events]
```

The important consequence: **tools and MCP servers can change between
turns** (toggled in Settings, or hot-reloaded via `/mcp`). The agent picks
up the change without a restart, because we re-read the registries every
turn.

## Reset semantics

`ChatRequest.reset == True` causes the route to call
`state.checkpointer.adelete_thread(req.id)` before streaming. Anything in
`app.db` (the message history) is left alone — only the LangGraph thread
state is wiped.

## Subagent calls inside a turn

```mermaid
flowchart LR
    A[Main agent] -- task tool call --> D[(dispatcher)]
    D --> S1[Subagent A]
    D --> S2[Subagent B]
    S1 --> T1[tool call]
    S1 --> R1[tool result]
    S2 --> T2[tool call]
    R1 -- providerMetadata.subagent.parentToolCallId --> Frontend
    T2 -- providerMetadata.subagent.parentToolCallId --> Frontend
```

The dispatcher tool is `task`. Its inner LLM tokens stay nested inside the
tool result on the frontend; only the **top-level** assistant text deltas
are streamed as plain text parts. See [Streaming](/modules/streaming/) for
the full story.
