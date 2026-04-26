# CLAUDE.md

Guidance for Claude Code in this repo.

## Repo layout

- `backend/` — FastAPI + LangGraph harness around local Ollama (default `gemma4:e4b`). Python 3.14, `uv`.
- `frontend/` — Next.js 16 (App Router, Turbopack) + React 19 + Tailwind v4 + shadcn/ui. Streams from backend via Vercel AI SDK 6.

## Commands

Backend (`cd backend`):
- Deps: `uv add <pkg>` — never edit `pyproject.toml`, never pin.
- Dev: `uv run uvicorn app.main:app --reload`
- Tests: `uv run pytest` (single: `uv run pytest tests/test_x.py::name`). `pytest.ini` has `asyncio_mode = auto`.
- Lint: `uv run ruff check` / `uv run ruff format`

Frontend (`cd frontend`):
- Dev: `npm run dev` · Build: `npm run build` · Typecheck: `npm run typecheck` · Lint: `npm run lint`
- Tests: `npm test` (vitest, jsdom). Single: `npx vitest run tests/Sidebar.test.tsx`

## Architecture

**Agent rebuilt per turn.** `POST /chat` ([backend/app/routes/chat.py](backend/app/routes/chat.py)) calls `build_agent_for_turn` each request — `ToolFlag` and `MCPServerConfig` change between turns. Only LLM, checkpointer, `MCPRegistry` live on `app.state` ([backend/app/main.py](backend/app/main.py) lifespan). Agent = `deepagents.create_deep_agent` with built-in `task` dispatcher. Subagents in `default_subagents()` ([backend/app/graphs/main_agent.py](backend/app/graphs/main_agent.py)); `tools` field = names resolved against live registry.

**Tool sources** ([backend/app/tool_registry.py](backend/app/tool_registry.py)):
- `discover_tools()` auto-imports `app/tools/*` and grabs `BaseTool` exports.
- MCP tools loaded by `MCPRegistry` ([backend/app/mcp_registry.py](backend/app/mcp_registry.py)) from `MCPServerConfig`, hot-reloaded via `/mcp`.
- `ToolFlag.enabled` filters merged list.

**Streaming = Vercel AI SDK 6 UI message stream.** [backend/app/streaming.py](backend/app/streaming.py) emits SSE for `@ai-sdk/react` `useChat`. Header `x-vercel-ai-ui-message-stream: v1` required. Subagent nesting: dispatcher tool calls (currently `{"task"}`) tracked by `tool_call_id`; inner tool events (non-empty `namespace`) tagged `providerMetadata.subagent.parentToolCallId`, grouped frontend-side by `getParentToolCallId` ([frontend/app/_components/ChatView.tsx](frontend/app/_components/ChatView.tsx)). Top-level text deltas forwarded; subagent LLM tokens stay inside tool result.

**Two SQLite DBs:**
- `app.db` — SQLModel (`ChatSession`, `ChatMessage`, `MCPServerConfig`, `ToolFlag`, `SavedArtifact`), async via `aiosqlite`, sessions from `app.db.async_session()`.
- `checkpoints.db` — LangGraph `AsyncSqliteSaver`, opened once in lifespan as context manager (keep inside `async with`). Reset thread: `state.checkpointer.adelete_thread(req.id)` when `req.reset`.

**Frontend shape:** `app/page.tsx` → `ChatShell` (sessions/artifacts/search state). `ChatView` uses `useChat` with `DefaultChatTransport` → `CHAT_URL`; `prepareSendMessagesRequest` sends `{id, messages, reset}` matching `ChatRequest` ([backend/app/schemas/chat.py](backend/app/schemas/chat.py)). `lib/api.ts` = REST client, `BACKEND` from `NEXT_PUBLIC_BACKEND_URL_BASE`. Tool render registry: `app/_components/tools/index.ts` maps name → component. Path alias `@/*` → `frontend/` root.

## Working rules

- **Other agents work here too.** Code/files you didn't touch may be in-progress work by another agent. Don't delete or refactor unfamiliar code as cleanup — leave it. Only modify what the task needs.
- **Small precise changes.** No drive-by refactors, renames, or cleanup unless asked. "Fix bug X" means fix bug X.
- **No unrequested fallbacks.** Let failures fail. No try/except swallowing, default values, retry loops, or graceful degradation unless asked. Surface real errors.
- **Comments explain *why*, not *what*.** Default = no comment. Write only for non-obvious constraints, invariants, workarounds.
- **Stay minimal.** No speculative abstractions, no helpers for one caller. Three similar lines beat premature abstraction.
- **Reuse before adding.** Look for existing logic to extract; duplicated logic across files = fix. Edit existing code over new branches.
- **Performance + reliability first.** Predictable under load, restarts, reconnects, partial streams.

## Quality gates

Hooks run automatically on every Edit/Write — `ruff check --fix` + `ruff format` for `*.py`, `prettier --write` + `eslint --fix` for `*.ts`/`*.tsx`. `Stop` hook runs `ruff check .` over backend as a session-end sanity pass. Don't bypass.

After non-trivial changes:
> Have code-reviewer audit the changes since last commit

Weekly hygiene (or before major refactors):
> Use dup-finder to scan for duplication and dead code

## Conventions

- Backend: loguru ([app/observability.py](backend/app/observability.py)); pydantic-settings ([app/config.py](backend/app/config.py), `.env`).
- Frontend: read `frontend/node_modules/next/dist/docs/` before Next.js APIs — training data older than installed Next 16.
- shadcn: `npx shadcn@latest add <name>` from `frontend/` → `components/ui/`.
