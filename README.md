# Local Gemma 4 Agentic Harness

FastAPI + LangGraph backend, Next.js 16 frontend, Postgres + Langfuse + MinIO + ClickHouse + Redis side-cars.

## Run with Docker Compose

### Prereqs

- Docker Desktop (or any Docker Engine + Compose v2)
- Free ports: `3010`, `4000`, `8000`, `9000`, `9001`

### 1. Configure secrets

Copy the example and fill it in:

```bash
cp .env.example .env
```

At minimum set `GOOGLE_API_KEY` (Gemini key from https://aistudio.google.com/apikey). Leave `LANGFUSE_SDK_*` blank for now — generated after first Langfuse login (see step 3).

The other random secrets (`POSTGRES_PASSWORD`, `LANGFUSE_SALT`, `LANGFUSE_ENCRYPTION_KEY`, `LANGFUSE_NEXTAUTH_SECRET`, etc.) can stay at the dev defaults in `.env` for local use, or regenerate:

```bash
openssl rand -hex 32   # for LANGFUSE_ENCRYPTION_KEY
openssl rand -base64 32   # for SALT / NEXTAUTH_SECRET
```

### 2. Bring the stack up

```bash
docker compose up -d --build
```

First build is slow (compiles Next.js, downloads Python deps). Re-runs use cache.

Check health:

```bash
docker compose ps
curl http://localhost:8000/health
```

### 3. (Optional) Wire Langfuse traces

1. Open http://localhost:4000 → Sign up. First user becomes the org owner.
2. New Organization → New Project.
3. Settings → API Keys → Create. Copy `pk-lf-…` and `sk-lf-…` (secret shown once).
4. Paste into `.env`:
   ```
   LANGFUSE_SDK_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SDK_SECRET_KEY=sk-lf-...
   ```
5. Reload the backend so it picks up the env:
   ```bash
   docker compose up -d backend
   ```

### Access

| Service | URL | Notes |
|---|---|---|
| Chat UI | http://localhost:3010 | Main app |
| Backend API | http://localhost:8000 | `/docs` for Swagger, `/health` for liveness |
| Langfuse | http://localhost:4000 | Sign up first; traces appear here |
| MinIO console | http://localhost:9001 | `minioadmin` / value of `MINIO_ROOT_PASSWORD` |
| MinIO S3 | http://localhost:9000 | S3 API used by Langfuse |

Postgres, Redis, ClickHouse stay on the internal `app-net` and are not exposed on the host. Use `docker compose exec` to reach them, e.g. `docker compose exec postgres psql -U postgres`.

### Common operations

```bash
# Tail backend logs
docker compose logs -f backend

# Rebuild after code changes
docker compose up -d --build backend frontend

# Stop everything
docker compose down

# Wipe all data (chat history, langfuse projects, MinIO) and start clean
docker compose down -v
```

### Notes

- `backend/data/skills/` and `backend/data/pptx_templates/` are bind-mounted read-only so playbooks/templates on the host show up immediately — no rebuild required.
- Chat history, uploads, generated decks live in the named volume `backend_data` and survive `docker compose down` (but not `down -v`).
- The frontend is built with `NEXT_PUBLIC_BACKEND_URL_BASE=http://localhost:8000` baked in. The browser hits the backend directly on the host port. CORS is configured for `http://localhost:3010`.

## Local development (without Docker)

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for the bare-metal setup (`uv run uvicorn ...` and `npm run dev`).
