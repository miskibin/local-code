---
title: Local development
description: Commands and quality gates for working in this repo.
---

## Backend

From `backend/`:

```bash
uv add <pkg>                                    # never edit pyproject.toml, never pin
uv run uvicorn app.main:app --reload            # dev server
uv run pytest                                   # all tests
uv run pytest tests/test_x.py::name             # single
uv run ruff check                               # lint
uv run ruff format                              # format
```

`pytest.ini` sets `asyncio_mode = auto`.

## Frontend

From `frontend/`:

```bash
npm run dev          # Next 16 + Turbopack
npm run build
npm run typecheck
npm run lint
npm test             # vitest, jsdom
npx vitest run tests/Sidebar.test.tsx   # single
```

`shadcn` components are added with `npx shadcn@latest add <name>` from
`frontend/`; output lands in `components/ui/`.

## Quality gates

Hooks run automatically on every Edit/Write:

- `*.py` → `ruff check --fix` then `ruff format`
- `*.ts`/`*.tsx` → `prettier --write` then `eslint --fix`
- `Stop` hook → `ruff check .` over backend as a session-end sanity pass

After non-trivial changes:

> Have code-reviewer audit the changes since last commit

Weekly hygiene (or before refactors):

> Use dup-finder to scan for duplication and dead code

## House rules (read these before changing anything)

- **Other agents work here too.** Code or files you didn't touch may be
  in-progress work by another agent. Don't refactor or delete unfamiliar
  code as cleanup — leave it.
- **Small, precise changes.** No drive-by renames or cleanup. "Fix bug X"
  means fix bug X.
- **No unrequested fallbacks.** Let failures fail. No try/except
  swallowing, default values, retry loops, or graceful degradation unless
  asked.
- **Comments explain *why*, not *what*.** Default = no comment.
- **Reuse before adding.** Look for existing logic first; duplicated logic
  across files is a bug to fix.
- **Trusted-client deployment.** Don't add auth gating, ownership filters,
  CSRF, or rate limits.
