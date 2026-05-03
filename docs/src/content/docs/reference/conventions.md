---
title: Conventions
description: How we write code here.
---

These mirror `CLAUDE.md`. Multiple agents work in this repo concurrently
— these rules keep them from stepping on each other.

## Working rules

- **Other agents work here too.** Code you didn't touch may be
  in-progress work. Don't refactor or delete unfamiliar code as
  cleanup.
- **Small, precise changes.** No drive-by refactors or renames.
- **No unrequested fallbacks.** Let failures fail. No try/except
  swallowing, retry loops, or default values.
- **Comments explain *why*, not *what*.** Default = no comment.
- **Reuse before adding.** Duplicated logic across files is a bug.
- **Trusted-client deployment.** Don't add auth gating, ownership
  filters, CSRF, or rate limits. `X-User-Email` is sufficient.

## Backend

- Logging: `loguru` (`app/observability.py`).
- Settings: `pydantic-settings` (`app/config.py`, `.env`).
- Deps: `uv add <pkg>` — never edit `pyproject.toml`, never pin.

## Frontend

- Read `frontend/node_modules/next/dist/docs/` before reaching for a
  Next.js API.
- shadcn: `npx shadcn@latest add <name>` from `frontend/`.
- Tailwind v4 — config is CSS-driven via `@theme` in `app/globals.css`.
- Path alias `@/*` → `frontend/` root.
