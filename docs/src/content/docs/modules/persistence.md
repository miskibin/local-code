---
title: Persistence
description: app.db and checkpoints.db — what they store and how they're opened.
---

There are **two** SQLite databases. They serve different roles and have
different lifetimes.

## `app.db` — application state

Driver: SQLModel + `aiosqlite`. Sessions come from
`app.db.async_session()`.

```mermaid
classDiagram
    class ChatSession {
      id: str (PK)
      user_email: str
      title: str
      created_at: datetime
    }
    class ChatMessage {
      id: int (PK)
      session_id: str (FK)
      role: "user|assistant|tool"
      content: str
      created_at: datetime
    }
    class MCPServerConfig {
      name: str (PK)
      enabled: bool
      connection: JSON
    }
    class ToolFlag {
      name: str (PK)
      enabled: bool
    }
    class SavedArtifact {
      id: int (PK)
      session_id: str
      kind: str
      payload: JSON
      created_at: datetime
    }
    ChatSession "1" --> "*" ChatMessage
    ChatSession "1" --> "*" SavedArtifact
```

## `checkpoints.db` — LangGraph thread state

Driver: `langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver`. Opened **once**
in `lifespan` as a context manager. Closing it tears down the writer.

```python
async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as saver:
    app.state.checkpointer = saver
    ...
    yield
```

Important: don't open another saver elsewhere. Anything that needs to
delete a thread should use the saver on `app.state`:

```python
await app.state.checkpointer.adelete_thread(req.id)
```

## Reset semantics

```mermaid
flowchart LR
    Reset[req.reset == true] --> CP[adelete_thread session.id]
    Reset -. unchanged .-> AppDB[(app.db rows)]
```

We deliberately **do not** wipe `ChatMessage` history on reset — only the
LangGraph checkpoint. This lets the user start a fresh agent run while
keeping the visible transcript.

## Migrations

There aren't any. SQLModel's `init_db()` runs `metadata.create_all` on
boot. If you change a model's schema in a way that needs migration, do
the migration explicitly.
