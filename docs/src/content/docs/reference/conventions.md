---
title: Conventions
description: How we write code in this repo. The minimal rules that everyone — humans and agents — should respect.
---

These mirror `CLAUDE.md` and exist because we have multiple agents
working in parallel. Cross-cutting rules keep them from stepping on each
other.

## Working rules

- **Other agents work here too.** Code or files you didn't touch may be
  in-progress work by another agent. Don't refactor or delete unfamiliar
  code as cleanup — leave it. Only modify what the task needs.
- **Small, precise changes.** No drive-by refactors, renames, or cleanup
  unless asked. "Fix bug X" means fix bug X.
- **No unrequested fallbacks.** Let failures fail. No try/except
  swallowing, default values, retry loops, or graceful degradation
  unless asked. Surface real errors.
- **Comments explain *why*, not *what*.** Default = no comment. Write
  one only for non-obvious constraints, invariants, or workarounds.
- **Stay minimal.** No speculative abstractions, no helpers for one
  caller. Three similar lines beat premature abstraction.
- **Reuse before adding.** Look for existing logic to extract; duplicated
  logic across files is a bug to fix.
- **Performance + reliability first.** Predictable under load, restarts,
  reconnects, partial streams.
- **Trusted-client deployment.** App runs behind trusted infra; clients
  are trusted. No per-route ownership / authorization checks needed.
  `X-User-Email` is sufficient identity. Don't add auth gating, ownership
  filters, CSRF, rate limits, or sandbox hardening unless asked — infra
  handles it.

## Backend specifics

- Logging: `loguru`, configured in `app/observability.py`.
- Settings: `pydantic-settings` in `app/config.py` (`.env`).
- Dependencies: `uv add <pkg>`. **Never** edit `pyproject.toml`. **Never**
  pin.
- Python: 3.14.

## Frontend specifics

- Read `frontend/node_modules/next/dist/docs/` before reaching for a
  Next.js API — training data is older than installed Next 16.
- shadcn: `npx shadcn@latest add <name>` from `frontend/` → output in
  `components/ui/`.
- Tailwind v4 — config is CSS-driven via `@theme` in `app/globals.css`.
- Path alias `@/*` → `frontend/` root.

## Quality gates

Hooks run automatically on Edit/Write:

- `*.py` → `ruff check --fix` + `ruff format`
- `*.ts` / `*.tsx` → `prettier --write` + `eslint --fix`
- `Stop` hook → `ruff check .` over backend as a session-end pass

After non-trivial changes:

> Have code-reviewer audit the changes since last commit

Weekly hygiene (or before refactors):

> Use dup-finder to scan for duplication and dead code
