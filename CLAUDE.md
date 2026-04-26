# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo layout

Two apps, no monorepo tooling.

- `backend/` — FastAPI + LangGraph agent harness around a local Ollama model (default `gemma4:e4b`). Python 3.14, managed with `uv`.
- `frontend/` — Next.js 16 (App Router, Turbopack) + React 19 + Tailwind v4 + shadcn/ui. Talks to backend via Vercel AI SDK 6 streaming.

## Common commands

### Backend (`cd backend`)

- Add deps: `uv add <pkg>` — never edit `pyproject.toml` directly, never pin versions.
- Dev server: `uv run uvicorn app.main:app --reload`
- All tests: `uv run pytest`
- Single test: `uv run pytest tests/test_streaming.py::test_name`
- Lint: `uv run ruff check` / `uv run ruff format`

`pytest.ini` sets `asyncio_mode = auto` — no `@pytest.mark.asyncio` needed.

### Frontend (`cd frontend`)

- Dev: `npm run dev` (Turbopack)
- Build: `npm run build`
- Typecheck: `npm run typecheck`
- Lint: `npm run lint`
- Tests: `npm test` (vitest, jsdom). Single file: `npx vitest run tests/Sidebar.test.tsx`

## Architecture

### Agent build is per-turn, not at startup

`POST /chat` ([backend/app/routes/chat.py](backend/app/routes/chat.py)) rebuilds the LangGraph agent on every request via `build_agent_for_turn`. Reason: tool flags (`ToolFlag` table) and MCP servers (`MCPServerConfig` table) can change between turns, so the tool list must be re-resolved. Only the LLM, checkpointer, and `MCPRegistry` live on `app.state` (set in [backend/app/main.py](backend/app/main.py) lifespan).

Agent itself is `deepagents.create_deep_agent` — wraps LangGraph with a built-in `task` dispatcher tool that spawns subagents in their own subgraph. Subagents declared in `default_subagents()` ([backend/app/graphs/main_agent.py](backend/app/graphs/main_agent.py)); their `tools` field is a list of tool names, resolved against the live registry per turn.

### Tools come from three sources, merged through `tool_registry`

[backend/app/tool_registry.py](backend/app/tool_registry.py):
- `discover_tools()` — auto-imports every module under `app/tools/` and grabs anything that is a `BaseTool`. Drop a new file in `app/tools/`, export a `BaseTool`, done.
- MCP tools — loaded by `MCPRegistry` ([backend/app/mcp_registry.py](backend/app/mcp_registry.py)) from the `MCPServerConfig` table, hot-reloaded via `/mcp` route.
- `ToolFlag` enabled flag filters the merged list.

### Streaming protocol matches Vercel AI SDK 6 UI message stream

[backend/app/streaming.py](backend/app/streaming.py) emits SSE events shaped for `@ai-sdk/react`'s `useChat`. Response header `x-vercel-ai-ui-message-stream: v1` is required.

Subagent nesting: when the model calls a `DISPATCHER_TOOLS` (currently `{"task"}`), `streaming.py` tracks the dispatcher's `tool_call_id`. Inner tool events from the resulting LangGraph subgraph (non-empty `namespace`) get tagged with `providerMetadata.subagent.parentToolCallId` so the frontend ([frontend/app/_components/ChatView.tsx](frontend/app/_components/ChatView.tsx) → `getParentToolCallId`) can group them under the parent card.

Top-level model text deltas are forwarded; subagent LLM tokens stay inside their tool result on purpose.

### Persistence: two SQLite DBs, on purpose

- `app.db` — SQLModel tables (`ChatSession`, `ChatMessage`, `MCPServerConfig`, `ToolFlag`, `SavedArtifact`). Async via `aiosqlite`, sessions from `app.db.async_session()`.
- `checkpoints.db` — LangGraph `AsyncSqliteSaver` for thread state. Opened once in lifespan as a context manager — keep it inside the `async with` block.

Resetting a thread: `state.checkpointer.adelete_thread(req.id)` when `req.reset` is true (regenerate-message path).

### Frontend shape

- `app/page.tsx` → `ChatShell` → owns sessions / artifacts / search-dialog state.
- `ChatView` uses `useChat` from `@ai-sdk/react` with a `DefaultChatTransport` pointing at `CHAT_URL`. `prepareSendMessagesRequest` sends `{id, messages, reset}` matching `ChatRequest` schema in [backend/app/schemas/chat.py](backend/app/schemas/chat.py).
- `lib/api.ts` is the single REST client; `BACKEND` from `NEXT_PUBLIC_BACKEND_URL_BASE` (default `http://localhost:8000`).
- Tool render registry in `app/_components/tools/` — `index.ts` maps tool name → React component. New tool = add file, register in index.

### Path alias

Frontend uses `@/*` → repo `frontend/` root (configured in `tsconfig.json` and `vitest.config.ts`).

## Working rules

- **Small precise changes.** Touch only what the task requires. No drive-by refactors, no renames "while we're here," no surrounding cleanup unless asked.
- **No unrequested fallbacks.** If something fails, let it fail. Do not add try/except swallowing, default values, retry loops, or graceful degradation unless the user explicitly asks. Surface the real error.
- **Comments explain *why*, not *what*.** Skip restating the code. Only write a comment when the reason is non-obvious — a constraint, an invariant, a workaround, surprising behavior. Default is no comment.
- **Stay minimal.** No speculative abstractions, no hypothetical-future hooks, no helper modules for one caller. Three similar lines beat a premature abstraction.
- **No bigger refactor than asked.** If the task is "fix bug X," fix bug X. Note adjacent issues separately; do not bundle them in.

## Core priorities

- **Performance and reliability first.** Behavior must stay predictable under load and during failures (session restarts, reconnects, partial streams). Prefer correctness and robustness over short-term convenience.
- **Maintainability is core, not optional.** Before adding new functionality, look for existing logic to extract or reuse. Duplicated logic across files is a smell — fix it. Don't take shortcuts by adding local one-off logic when shared logic belongs in a module. Editing existing code is preferred over piling on new branches.

## Conventions worth knowing

- Backend: loguru for logging (configured in `app/observability.py`); pydantic-settings for config (`app/config.py`, env file `.env`).
- Frontend (`AGENTS.md`): before touching Next.js APIs, read the bundled docs in `frontend/node_modules/next/dist/docs/` — training data is older than the installed Next 16.
- shadcn components: `npx shadcn@latest add <name>` from `frontend/`. They land in `components/ui/`.
