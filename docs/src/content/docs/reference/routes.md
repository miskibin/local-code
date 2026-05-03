---
title: REST routes
description: One-line summary per router.
---

Each file in `backend/app/routes/` exposes a single
`router = APIRouter()` included from `app/main.py:create_app`.

| Router                  | Path prefix         | Owns                                            |
| ----------------------- | ------------------- | ----------------------------------------------- |
| `auth.py`               | `/auth/*`           | `X-User-Email` → user.                          |
| `chat.py`               | `/chat`             | The streaming turn (AI SDK 6).                  |
| `sessions.py`           | `/sessions/*`       | List / create / rename / delete chats.          |
| `tools.py`              | `/tools[/{name}]`   | List + toggle `ToolFlag`.                       |
| `mcp.py`                | `/mcp[/{name}]`     | CRUD MCP servers, hot-reload.                   |
| `commands.py`           | `/commands`         | Discovered slash commands.                      |
| `artifacts.py`          | `/artifacts/*`      | List / upload / refresh / delete.               |
| `tasks.py`              | `/tasks/*`          | CRUD + import / export / generate.              |
| `skills.py`             | `/skills/*`         | List / configure skills.                        |
| `feedback.py`           | `/feedback`         | Submit feedback.                                |
| `user_instructions.py`  | `/user/instructions`| Per-user prompt.                                |

`GET /health` is defined inline in `create_app` for the Docker
healthcheck.

For the full per-method shapes, read the route file — they're each ~50
lines and the pydantic schemas in `backend/app/schemas/` are the
contract.
