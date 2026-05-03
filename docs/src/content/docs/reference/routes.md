---
title: REST routes
description: A flat inventory of HTTP endpoints, grouped by router.
---

All routes live under `backend/app/routes/`. Each file exposes a single
`router = APIRouter()` that's included from `app/main.py:create_app`.

## auth (`routes/auth.py`)

| Method | Path           | Notes                            |
| ------ | -------------- | -------------------------------- |
| POST   | `/auth/login`  | Resolves `X-User-Email` to user. |
| GET    | `/auth/me`     | Current user.                    |

## chat (`routes/chat.py`)

| Method | Path    | Notes                                                                |
| ------ | ------- | -------------------------------------------------------------------- |
| POST   | `/chat` | Streams the AI SDK 6 UI message stream. Body: `{id, messages, reset}`. |

## sessions (`routes/sessions.py`)

| Method | Path                          | Notes                                |
| ------ | ----------------------------- | ------------------------------------ |
| GET    | `/sessions`                   | List the user's sessions.            |
| POST   | `/sessions`                   | Create a session.                    |
| PATCH  | `/sessions/{sid}`             | Rename, etc.                         |
| GET    | `/sessions/{sid}/messages`    | Persisted UI messages for a session. |
| DELETE | `/sessions/{sid}`             | Removes session + its checkpoint.    |

## tools (`routes/tools.py`)

| Method | Path                  | Notes                              |
| ------ | --------------------- | ---------------------------------- |
| GET    | `/tools`              | All tools (local + MCP) + flags.   |
| PATCH  | `/tools/{name}`       | Toggle a `ToolFlag`.               |

## mcp (`routes/mcp.py`)

| Method | Path                  | Notes                              |
| ------ | --------------------- | ---------------------------------- |
| GET    | `/mcp`                | List server configs.               |
| POST   | `/mcp`                | Add a server, sync registry.       |
| PATCH  | `/mcp/{name}/me`      | Update + sync.                     |
| DELETE | `/mcp/{name}`         | Remove + sync.                     |

## commands (`routes/commands.py`)

| Method | Path        | Notes                                  |
| ------ | ----------- | -------------------------------------- |
| GET    | `/commands` | Discovered slash commands + arg hints. |

## artifacts (`routes/artifacts.py`)

| Method | Path                          | Notes                       |
| ------ | ----------------------------- | --------------------------- |
| GET    | `/artifacts`                  | List for current user.      |
| GET    | `/artifacts/{aid}`            | Fetch single artifact DTO.  |
| POST   | `/artifacts`                  | Create.                     |
| POST   | `/artifacts/{aid}/refresh`    | Regenerate.                 |
| POST   | `/artifacts/upload`           | Upload arbitrary file.      |
| DELETE | `/artifacts/{aid}`            | Delete.                     |
| GET    | `/artifacts/{aid}/file`       | Stream the file payload.    |

## tasks (`routes/tasks.py`)

| Method | Path                       | Notes                |
| ------ | -------------------------- | -------------------- |
| GET    | `/tasks`                   | List.                |
| GET    | `/tasks/{tid}`             | Single.              |
| PUT    | `/tasks/{tid}`             | Update.              |
| POST   | `/tasks/validate`          | Validate a task DTO. |
| DELETE | `/tasks/{tid}`             | Delete.              |
| GET    | `/tasks/{tid}/export`      | Export DTO.          |
| POST   | `/tasks/import`            | Import.              |
| POST   | `/tasks/generate`          | Generate from prompt.|

## skills (`routes/skills.py`)

| Method | Path                          | Notes                  |
| ------ | ----------------------------- | ---------------------- |
| GET    | `/skills`                     | List skills.           |
| PATCH  | `/skills/{name}`              | Toggle / configure.    |
| GET    | `/skills/{name}/content`      | Skill markdown body.   |

## feedback (`routes/feedback.py`)

| Method | Path        | Notes                  |
| ------ | ----------- | ---------------------- |
| POST   | `/feedback` | Submit feedback.       |

## user instructions (`routes/user_instructions.py`)

| Method | Path                  | Notes              |
| ------ | --------------------- | ------------------ |
| GET    | `/user/instructions`  | Per-user prompt.   |
| PUT    | `/user/instructions`  | Update.            |

## health

`GET /health` — defined inline in `create_app`. Returns `{"status":
"ok"}`. Used by the Docker stack's healthcheck.
