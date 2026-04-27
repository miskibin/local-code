# Backend

FastAPI + LangGraph agentic harness over local Ollama.

## Setup

```bash
uv sync
```

### Deno (required for `python_exec` sandbox)

`python_exec` runs LLM-authored Python in a Pyodide WASM sandbox via
[`langchain-sandbox`](https://github.com/langchain-ai/langchain-sandbox), which
shells out to a Deno subprocess. Deno **2.4+** is required (older versions
lack the V8 stack-switching support Pyodide's matplotlib needs).

Install (Windows PowerShell):

```powershell
irm https://deno.land/install.ps1 | iex
```

Linux/macOS:

```bash
curl -fsSL https://deno.land/install.sh | sh
```

Verify:

```bash
deno --version   # expect 2.4+
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

The lifespan logs `python sandbox ready: ...` once Deno + Pyodide are wired
up. If Deno is missing, startup fails with a pointer back to the install URL.
