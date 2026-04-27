```markdown
# GitHub Copilot Instructions

GitHub Copilot is used in this repo **for code review only** — it does not implement changes or run commands. The notes below are what Copilot should weigh when reviewing a PR.

## Project overview

- `backend/` — FastAPI + LangGraph harness around local Ollama (default `gemma4:e4b`). Python 3.14, managed with `uv`.
- `frontend/` — Next.js 16 (App Router, Turbopack) + React 19 + Tailwind v4 + shadcn/ui. Streams from backend via Vercel AI SDK 6.

## Architecture context for reviewers

### Agent rebuilt per turn
`POST /chat` (`backend/app/routes/chat.py`) calls `build_agent_for_turn` on every request because `ToolFlag` and `MCPServerConfig` may change between turns. Only the LLM, checkpointer, and `MCPRegistry` live on `app.state` (`backend/app/main.py` lifespan). Flag any change that moves per-turn state onto `app.state`, or that caches an agent across turns.

### Tool sources (`backend/app/tool_registry.py`)
- `discover_tools()` auto-imports `app/tools/*` and collects `BaseTool` exports.
- MCP tools are loaded by `MCPRegistry` (`backend/app/mcp_registry.py`) from `MCPServerConfig`, hot-reloaded via `/mcp`.
- `ToolFlag.enabled` filters the merged list.

Reviewers: new tools should be discoverable through these paths, not hand-registered.

### Streaming
Vercel AI SDK 6 UI message stream. `backend/app/streaming.py` emits SSE for `@ai-sdk/react`'s `useChat`. The header `x-vercel-ai-ui-message-stream: v1` is required.

Subagent nesting: dispatcher tool calls (currently `{"task"}`) are tracked by `tool_call_id`; inner tool events (non-empty `namespace`) are tagged with `providerMetadata.subagent.parentToolCallId` and grouped frontend-side by `getParentToolCallId` (`frontend/app/_components/ChatView.tsx`). Top-level text deltas are forwarded; subagent LLM tokens stay inside their tool result.

Reviewers: changes to the SSE shape, the required header, or the parent/child tool-call linkage will silently break the frontend renderer — call them out.

### Two SQLite databases
- `app.db` — SQLModel (`ChatSession`, `ChatMessage`, `MCPServerConfig`, `ToolFlag`, `SavedArtifact`), async via `aiosqlite`, sessions from `app.db.async_session()`.
- `checkpoints.db` — LangGraph `AsyncSqliteSaver`, opened once in lifespan as a context manager. Usage must stay inside `async with`. Reset a thread with `state.checkpointer.adelete_thread(req.id)` when `req.reset`.

### Frontend shape
`app/page.tsx` → `ChatShell` (sessions, artifacts, search state). `ChatView` uses `useChat` with `DefaultChatTransport` pointing at `CHAT_URL`; `prepareSendMessagesRequest` sends `{id, messages, reset}` matching `ChatRequest` (`backend/app/schemas/chat.py`). `lib/api.ts` is the REST client, `BACKEND` comes from `NEXT_PUBLIC_BACKEND_URL_BASE`. Tool render registry: `app/_components/tools/index.ts` maps tool name → component. Path alias `@/*` → `frontend/` root.

Reviewers: changes to `ChatRequest` must be matched on both sides.

## What to flag in review

- **Scope creep.** Drive-by refactors, renames, or cleanup outside the stated task. "Fix bug X" should fix bug X — nothing else.
- **Touching unrelated files.** Other agents may have in-progress work in this repo. Modifications to files unrelated to the PR's purpose are suspicious; flag them.
- **Unrequested fallbacks.** Try/except blocks that swallow errors, default values masking missing data, retry loops, graceful degradation — none of these belong unless explicitly asked for. Errors should surface.
- **Speculative abstractions.** Helpers introduced for a single caller, generic interfaces with one implementation, premature parameterization. Three similar lines are preferable to a premature abstraction.
- **Duplication.** Logic that already exists elsewhere should be reused rather than re-implemented. Cross-file duplication is a defect.
- **Comments that explain *what* instead of *why*.** Default to no comment. Comments are warranted only for non-obvious constraints, invariants, or workarounds. Flag narration of the obvious.
- **Performance and reliability regressions.** Behavior under load, restarts, reconnects, and partial streams must stay predictable. Synchronous I/O on hot paths, unbounded buffers, or anything that breaks streaming should be called out.
- **Bypassed quality gates.** Hooks run `ruff check --fix` + `ruff format` on Python and `prettier --write` + `eslint --fix` on TS/TSX. PRs should not disable, skip, or work around these.

## Conventions

- **Backend logging:** loguru via `backend/app/observability.py`. Direct `print` or stdlib `logging` calls are a smell.
- **Backend config:** pydantic-settings (`backend/app/config.py`, `.env`). New config should land here, not as ad-hoc `os.getenv` reads.
- **Backend deps:** added via `uv add <pkg>`. Manual edits to `pyproject.toml` or pinned versions should be questioned.
- **Frontend Next.js APIs:** the source of truth is `frontend/node_modules/next/dist/docs/` (Next 16). Suggestions based on older Next idioms (pages router, `getServerSideProps`, etc.) are likely wrong.
- **Imports (frontend):** use the `@/*` alias from `frontend/` root.
- **shadcn components:** added via `npx shadcn@latest add <name>` into `components/ui/`. Hand-rolled equivalents should be questioned.
```
