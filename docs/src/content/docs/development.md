---
title: Local development
description: Commands and gates.
---

## Backend (`cd backend`)

```bash
uv add <pkg>                              # never edit pyproject.toml, never pin
uv run uvicorn app.main:app --reload      # dev
uv run pytest                             # tests (asyncio_mode = auto)
uv run ruff check / format                # lint
```

## Frontend (`cd frontend`)

```bash
npm run dev                               # Next 16 + Turbopack
npm run build / typecheck / lint
npm test                                  # vitest, jsdom
npx shadcn@latest add <name>              # adds to components/ui/
```

## Quality gates

Hooks fire on every Edit/Write:

- `*.py` → `ruff check --fix` + `ruff format`
- `*.ts`/`*.tsx` → `prettier --write` + `eslint --fix`
- `Stop` → `ruff check .` over backend

After non-trivial work: ask the **code-reviewer** agent. Weekly:
**dup-finder**.

See [Conventions](/reference/conventions/) for the working rules.
