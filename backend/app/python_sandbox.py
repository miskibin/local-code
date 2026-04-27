"""Pyodide sandbox for `python_exec` tool.

Replaces a host subprocess (sys.executable -I -c ...) with a Deno + Pyodide
WASM sandbox. Agent code runs in WASM with Deno-enforced permissions:
- read: only sessions dir, deno cache, node_modules, cwd
- write: only sessions dir
- net: only Pyodide CDN + PyPI (for package loading)
- env / run / ffi: denied

Stateful per-`session_id`: Python globals (variables, imports, DataFrames)
persist across `execute()` calls scoped to a chat thread, so the agent can
iterate (load → inspect → plot) without re-staging. State is serialised to
`{sessions_dir}/{session_id}/session.pkl` by Deno; clearing the directory
resets the thread's python globals.

We invoke Deno directly with `-f tempfile.py` instead of going through
`PyodideSandbox.execute()` because the upstream `-c` code path applies a
`replace(/\\n/g, "\n")` to its argument that mangles Python source — any
`"\n"` string literal becomes a real newline mid-string and the script
fails to parse. The file path doesn't trigger that replacement.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_sandbox import PyodideSandbox
from langchain_sandbox.pyodide import PKG_NAME
from loguru import logger

from app.config import get_settings

_INVALID_SESSION_CHAR = re.compile(r"[^a-zA-Z0-9_-]")


def _slug_session(session_id: str) -> str:
    # Deno wrapper enforces ^[a-zA-Z0-9_-]+$ on session names. Frontend
    # ChatSession.id is unconstrained — slugify to keep callers honest while
    # remaining deterministic so reset_session() and execute_code() agree.
    return _INVALID_SESSION_CHAR.sub("_", session_id) or "default"


def _deno_cache_dir() -> str:
    # Deno's user cache; required for read so the wrapper can load the cached
    # pyodide.asm.wasm and npm packages without granting full filesystem read.
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return str(Path(base) / "deno")
    cache = os.environ.get("DENO_DIR")
    if cache:
        return cache
    return str(Path.home() / ".cache" / "deno")


def build_sandbox() -> PyodideSandbox:
    settings = get_settings()
    sessions_dir = Path(settings.python_sessions_dir).resolve()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    deno_cache = _deno_cache_dir()
    cwd = os.getcwd()

    # Narrowed read list blocks `js.Deno.readTextFile(...)` escapes from
    # agent code — without this Pyodide-Python could read host files via
    # the JS bridge even though Python's own `open()` is jailed in MEMFS.
    sandbox = PyodideSandbox(
        sessions_dir=str(sessions_dir),
        allow_net=list(settings.python_sandbox_allow_net),
        allow_read=[str(sessions_dir), deno_cache, "node_modules", cwd],
        allow_write=[str(sessions_dir)],
    )
    logger.info(
        f"python sandbox ready: sessions={sessions_dir} "
        f"net={settings.python_sandbox_allow_net}"
    )
    return sandbox


def reset_session(session_id: str) -> None:
    """Delete persisted Python globals for a chat thread.

    Called on chat reset so the next `python_exec` starts with empty globals.
    Otherwise agent would see "fresh chat, stale df" — confusing.
    """
    settings = get_settings()
    target = Path(settings.python_sessions_dir).resolve() / _slug_session(session_id)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def ensure_deno() -> str:
    """Resolve `deno` on PATH; raise at boot if missing."""
    deno = shutil.which("deno")
    if not deno:
        raise RuntimeError(
            "Deno binary not found on PATH. python_exec sandbox needs Deno. "
            "Install: https://docs.deno.com/runtime/getting_started/installation/"
        )
    return deno


@dataclass(slots=True)
class SandboxResult:
    status: str  # "success" | "error"
    stdout: str | None
    stderr: str | None
    result: Any | None = None


async def execute_code(
    sandbox: PyodideSandbox,
    code: str,
    *,
    session_id: str | None = None,
    timeout_seconds: float | None = None,
) -> SandboxResult:
    """Run `code` in the sandbox via `-f tempfile`. See module docstring for why."""
    deno = ensure_deno()
    sid = _slug_session(session_id) if session_id else None

    sessions_dir = sandbox.sessions_dir
    Path(sessions_dir).mkdir(parents=True, exist_ok=True)

    # Code file lives under sessions_dir so the existing --allow-read/write
    # entries cover it without widening permissions. We pass `-f <basename>`
    # and set the subprocess cwd to the file's dir because the wrapper joins
    # non-`/`-prefixed paths with Deno.cwd() and Windows absolute paths
    # (`C:\...`) don't pass that prefix check.
    fd, path = tempfile.mkstemp(prefix="exec_", suffix=".py", dir=sessions_dir)
    os.close(fd)
    Path(path).write_text(code, encoding="utf-8")
    # Run with cwd at backend root so Deno reuses the cached node_modules/pyodide
    # there instead of re-fetching every call. Relative path lets the wrapper's
    # `join(Deno.cwd(), file)` resolve correctly on Windows (where absolute paths
    # don't pass its `startsWith("/")` check). Falls back to sessions_dir as cwd
    # when sessions_dir lives on a different drive than cwd (Windows-only quirk).
    deno_cwd = os.getcwd()
    try:
        rel_path = os.path.relpath(path, start=deno_cwd)
    except ValueError:
        deno_cwd = sessions_dir
        rel_path = os.path.relpath(path, start=deno_cwd)
    cmd = [deno, "run", *sandbox.permissions, PKG_NAME, "-f", rel_path, "-d", sessions_dir]
    if sid:
        cmd.extend(["-s", sid])

    # Capture via subprocess.run + capture_output — keeps both streams in
    # memory; tested as the most reliable transport for the wrapper's
    # JSON-on-stdout pattern across Windows/Linux + sync/async contexts.
    logger.debug(f"sandbox cmd: {' '.join(cmd)}")
    logger.debug(f"code file: {path}")

    def _run() -> tuple[bytes, bytes, int]:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            cwd=deno_cwd,
            timeout=timeout_seconds,
            check=False,
        )
        return proc.stdout, proc.stderr, proc.returncode

    try:
        try:
            stdout_b, stderr_b, _rc = await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired:
            return SandboxResult(
                status="error",
                stdout=None,
                stderr=f"Execution timed out after {timeout_seconds}s",
            )
    finally:
        Path(path).unlink(missing_ok=True)

    raw = stdout_b.decode("utf-8", errors="replace")
    if not raw.strip():
        err_msg = stderr_b.decode("utf-8", errors="replace") or None
        if err_msg is None and _rc != 0:
            err_msg = f"deno exit {_rc}, no output"
        logger.debug(f"python sandbox raw empty stdout, rc={_rc}, cmd={cmd}, stderr={err_msg!r}")
        return SandboxResult(status="error", stdout=None, stderr=err_msg)
    try:
        full = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("python sandbox produced non-JSON stdout (truncated): {}", raw[:200])
        return SandboxResult(status="error", stdout=raw, stderr=None)
    return SandboxResult(
        status="success" if full.get("success") else "error",
        stdout=full.get("stdout"),
        stderr=full.get("stderr") or full.get("error"),
        result=full.get("result"),
    )
