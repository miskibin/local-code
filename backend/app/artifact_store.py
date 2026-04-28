"""Single source of truth for artifact creation, hydration, and refresh.

Tools and the /artifacts/{id}/refresh route both go through here so write paths
stay in one place. Per-kind executors live below; pick one via `source_kind`.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from sqlalchemy import create_engine, text
from sqlmodel import select

from app.config import get_settings
from app.db import async_session
from app.models import SavedArtifact
from app.utils import ARTIFACT_ID_RE, now_utc

SOURCE_CODE_MAX = 64 * 1024
PAYLOAD_MAX_BYTES = 1 * 1024 * 1024
SQL_ROW_CAP = 200
PY_TIMEOUT_SECONDS = 20
ARTIFACT_START = "<<ARTIFACT::start>>"
ARTIFACT_END = "<<ARTIFACT::end>>"


def _truncate_source(code: str | None) -> tuple[str | None, bool]:
    if code is None:
        return None, False
    encoded = code.encode("utf-8")
    if len(encoded) <= SOURCE_CODE_MAX:
        return code, False
    return encoded[:SOURCE_CODE_MAX].decode("utf-8", errors="ignore"), True


def _payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _cap_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], int, bool]:
    size = _payload_size(payload)
    if size <= PAYLOAD_MAX_BYTES:
        return payload, size, False
    capped: dict[str, Any] = dict(payload)
    if isinstance(capped.get("rows"), list):
        rows = capped["rows"]
        keep = max(1, len(rows) // 4)
        capped["rows"] = rows[:keep]
        capped["truncated"] = True
        capped["truncated_reason"] = f"payload exceeded {PAYLOAD_MAX_BYTES} bytes"
    return capped, _payload_size(capped), True


async def create_artifact(
    *,
    owner_id: str,
    kind: str,
    title: str,
    payload: dict[str, Any],
    summary: str,
    source_kind: str | None,
    source_code: str | None,
    parent_artifact_ids: list[str] | None = None,
    session_id: str | None = None,
    artifact_id: str | None = None,
) -> SavedArtifact:
    capped_payload, size, _ = _cap_payload(payload)
    code, _ = _truncate_source(source_code)
    aid = artifact_id or f"art_{uuid4().hex[:12]}"
    now = now_utc()
    row = SavedArtifact(
        id=aid,
        owner_id=owner_id,
        session_id=session_id,
        kind=kind,
        title=title,
        payload=capped_payload,
        summary=summary[:500],
        source_kind=source_kind,
        source_code=code,
        parent_artifact_ids=list(parent_artifact_ids or []),
        payload_size=size,
        created_at=now,
        updated_at=now,
    )
    async with async_session() as s:
        s.add(row)
        await s.commit()
        await s.refresh(row)
    return row


async def get_artifact(artifact_id: str) -> SavedArtifact | None:
    async with async_session() as s:
        return await s.get(SavedArtifact, artifact_id)


async def refresh_artifact(artifact_id: str) -> SavedArtifact:
    async with async_session() as s:
        row = await s.get(SavedArtifact, artifact_id)
        if row is None:
            raise LookupError(f"artifact {artifact_id} not found")
        if not row.source_kind or row.source_code is None:
            raise ValueError(f"artifact {artifact_id} has no source to refresh")
        source_kind = row.source_kind
        source_code = row.source_code
        parent_ids = list(row.parent_artifact_ids or [])

    result = await _run_executor(source_kind, source_code, parent_artifact_ids=parent_ids)

    async with async_session() as s:
        row = await s.get(SavedArtifact, artifact_id)
        if row is None:
            raise LookupError(f"artifact {artifact_id} not found")
        capped_payload, size, _ = _cap_payload(result["payload"])
        row.kind = result.get("kind", row.kind)
        row.title = result.get("title", row.title)
        row.payload = capped_payload
        row.summary = result.get("summary", row.summary)[:500]
        row.payload_size = size
        row.updated_at = now_utc()
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row


async def _run_executor(
    source_kind: str, source_code: str, parent_artifact_ids: list[str]
) -> dict[str, Any]:
    if source_kind == "python":
        return await run_python_artifact(source_code)
    if source_kind == "sql":
        return await run_sql_artifact(source_code)
    if source_kind == "text":
        return {
            "kind": "text",
            "title": "Text",
            "payload": {"text": source_code},
            "summary": source_code.splitlines()[0][:200] if source_code else "",
        }
    raise ValueError(f"unknown source_kind: {source_kind}")


# ---------- Python executor ----------

import ast  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

_ART_PATHS_ENV = "LC_ARTIFACT_PATHS"
_FONT_DIR_ENV = "LC_MPL_FONT_DIR"
_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_PROJECT_ROOT_ENV = "LC_PROJECT_ROOT"
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])

# Modules that give the agent SQL/network/process power we don't want it to have.
# Caught at AST level before the subprocess starts. Runtime escapes (importlib,
# getattr tricks) are backstopped by the audit hook in the preamble.
_BLOCKED_USER_IMPORTS = frozenset(
    {
        # SQL / DB drivers (use sql_query / sql-agent instead)
        "sqlite3",
        "aiosqlite",
        "sqlalchemy",
        "asyncpg",
        "psycopg",
        "psycopg2",
        "pymongo",
        "redis",
        "pymysql",
        "mysql",
        "oracledb",
        "pyodbc",
        "duckdb",
        # Network
        "socket",
        "ssl",
        "urllib",
        "urllib3",
        "http",
        "httpx",
        "requests",
        "aiohttp",
        "websockets",
        "ftplib",
        "smtplib",
        "telnetlib",
        "paramiko",
        # Process escape
        "subprocess",
        "multiprocessing",
        # Loader / FFI escapes
        "ctypes",
        "_ctypes",
        "importlib",
        "builtins",
    }
)

# Names that, if called as bare functions, give code-injection or import bypass.
_BLOCKED_USER_CALLABLES = frozenset({"__import__", "exec", "eval", "compile"})

# `os.X` attribute accesses we reject. Path/env helpers (os.path, os.getcwd,
# os.environ) stay available — they're inert.
_BLOCKED_OS_ATTRS = frozenset(
    {
        "system",
        "popen",
        "exec",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "spawn",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "fork",
        "forkpty",
        "kill",
    }
)


def _validate_user_code(code: str) -> None:
    """AST-level denylist for python_exec input.

    Raises ValueError on any disallowed import / call. Runtime escapes are
    backstopped by the audit hook in the subprocess preamble.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"python_exec: syntax error: {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top in _BLOCKED_USER_IMPORTS:
                    raise ValueError(
                        f"python_exec: import of {alias.name!r} is blocked "
                        f"(no DB / network / subprocess from python_exec)"
                    )
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".", 1)[0]
            if top in _BLOCKED_USER_IMPORTS:
                raise ValueError(f"python_exec: import from {node.module!r} is blocked")
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in _BLOCKED_USER_CALLABLES:
                raise ValueError(f"python_exec: call to {f.id!r} is blocked")
            if (
                isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name)
                and f.value.id == "os"
                and f.attr in _BLOCKED_OS_ATTRS
            ):
                raise ValueError(f"python_exec: os.{f.attr} is blocked")


_PY_PRELUDE = textwrap.dedent(
    f"""
    import json as _json, sys as _sys, os as _os

    # Resource limits + audit hook BEFORE anything else runs. Audit hooks
    # can't be removed once installed (CPython enforces this at C level),
    # so user code can't disable these from the script body.
    try:
        import resource as _resource
        _resource.setrlimit(_resource.RLIMIT_CPU, (30, 30))
        _resource.setrlimit(_resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
        _resource.setrlimit(_resource.RLIMIT_FSIZE, (50 * 1024 ** 2, 50 * 1024 ** 2))
    except (ImportError, ValueError, OSError):
        pass  # non-POSIX (Windows) or already lower

    _SANDBOX_CWD = _os.path.abspath(_os.getcwd())
    _PROJECT_ROOT = _os.environ.get({_PROJECT_ROOT_ENV!r}, "")
    # Anything under sys.prefix (venv root or system Python install) is the
    # interpreter's own files — must stay readable so imports work.
    _PY_PREFIX = _os.path.abspath(_sys.prefix) + _os.sep
    _PY_BASE_PREFIX = _os.path.abspath(_sys.base_prefix) + _os.sep
    # Trusted bundled font dir — matplotlib's FT2Font lazily opens TTFs the
    # first time text renders (after the hook is installed), so we must allow
    # reads under this dir to keep `out_image` working.
    _FONT_DIR_PATH = _os.environ.get({_FONT_DIR_ENV!r}, "")
    _FONT_DIR_PREFIX = (_os.path.abspath(_FONT_DIR_PATH) + _os.sep) if _FONT_DIR_PATH else ""

    def _sb_writable(p):
        if isinstance(p, int):
            return True
        try:
            ap = _os.path.abspath(_os.fspath(p))
        except TypeError:
            return True
        return ap == _SANDBOX_CWD or ap.startswith(_SANDBOX_CWD + _os.sep)

    def _sb_dangerous_read(p):
        if isinstance(p, int):
            return False
        try:
            ap = _os.path.abspath(_os.fspath(p))
        except TypeError:
            return False
        # Allow Python stdlib + site-packages reads (covers venv and system).
        if ap.startswith(_PY_PREFIX) or ap.startswith(_PY_BASE_PREFIX):
            return False
        if _FONT_DIR_PREFIX and ap.startswith(_FONT_DIR_PREFIX):
            return False
        base = _os.path.basename(ap)
        if base.endswith(".db") or base.startswith(".env"):
            return True
        if _PROJECT_ROOT and ap.startswith(_PROJECT_ROOT + _os.sep):
            return True
        return False

    def _sb_audit(event, args):
        if event == "open":
            file = args[0] if args else None
            mode = args[1] if len(args) > 1 else "r"
            if file is None:
                return
            if mode and any(c in mode for c in "wax+") and not _sb_writable(file):
                raise PermissionError("sandbox: write outside sandbox blocked: " + repr(file))
            if _sb_dangerous_read(file):
                raise PermissionError("sandbox: read of project file / db blocked: " + repr(file))
        elif event in ("socket.connect", "socket.bind", "socket.getaddrinfo"):
            raise PermissionError("sandbox: network access blocked")
        elif event in ("subprocess.Popen", "os.system", "os.exec"):
            raise PermissionError("sandbox: subprocess / os.system blocked")
        # Note: `ctypes.dlopen` is intentionally NOT blocked here. The AST
        # validator already rejects `import ctypes` / `_ctypes` / `__import__`
        # / `importlib`, so user code has no direct path to dlopen. Allowed
        # libs (numpy, matplotlib, scipy, sklearn) load native extensions on
        # Windows at import / first-use time — blocking dlopen here breaks
        # them. Network / subprocess / file audit events still fire from C
        # code, so a malicious DLL would still trip those.

    def _apply_app_mpl_style():
        import os as _os, glob as _glob
        try:
            import matplotlib as _mpl
            _mpl.use("Agg")
        except ImportError:
            return
        _font_dir = _os.environ.get({_FONT_DIR_ENV!r})
        if _font_dir:
            try:
                from matplotlib import font_manager as _fm
                for _ttf in _glob.glob(_os.path.join(_font_dir, "*.ttf")):
                    _fm.fontManager.addfont(_ttf)
            except Exception as _e:
                _sys.stderr.write(
                    f"warning: mpl font load failed: {{type(_e).__name__}}: {{_e}}\\n"
                )
        from cycler import cycler as _cycler
        # Split ink: body text reads on white; spines/grid stay softer so bars stay the focus.
        _ink_text = "#1f1f1f"
        _ink_spine = "#6b6b6b"
        _grid = "#c8c8c8"
        _mpl.rcParams.update({{
            "figure.facecolor": "none",
            "figure.edgecolor": "none",
            "figure.dpi": 120,
            "axes.facecolor": "none",
            "axes.edgecolor": _ink_spine,
            "axes.labelcolor": _ink_text,
            "axes.titlecolor": _ink_text,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.labelweight": "medium",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.prop_cycle": _cycler(color=[
                "#3b82f6", "#10b981", "#f59e0b",
                "#ec4899", "#8b5cf6", "#06b6d4",
            ]),
            "grid.color": _grid,
            "grid.alpha": 0.28,
            "grid.linestyle": ":",
            "text.color": _ink_text,
            "xtick.color": _ink_text,
            "ytick.color": _ink_text,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "font.size": 11,
            "font.weight": "medium",
            "font.family": ["Geist Mono", "DejaVu Sans Mono", "monospace"],
            "legend.frameon": False,
            "legend.fontsize": 10,
            "legend.labelcolor": _ink_text,
            "savefig.facecolor": "none",
            "savefig.edgecolor": "none",
            "savefig.transparent": True,
        }})

    _sys.addaudithook(_sb_audit)

    _apply_app_mpl_style()

    def out(_obj):
        _sys.stdout.write({ARTIFACT_START!r})
        _sys.stdout.write(_json.dumps(_obj, default=str))
        _sys.stdout.write({ARTIFACT_END!r})
        _sys.stdout.write("\\n")

    def out_sql_list(items, *, quote="'"):
        # Format an iterable as a SQL fragment for IN(...) / column lists, e.g.
        # ['GenreId','AlbumId'] -> "'GenreId', 'AlbumId'". Pass quote='"' for
        # identifier lists, quote='' for already-safe tokens. Trusted-input
        # only: not an injection-safe quoter.
        _q = quote
        if _q:
            out(", ".join(f"{{_q}}{{str(x).replace(_q, _q*2)}}{{_q}}" for x in items))
        else:
            out(", ".join(str(x) for x in items))

    def out_image(fig=None, *, title=None, caption=None):
        import io as _io, base64 as _b64
        import matplotlib.pyplot as _plt
        f = fig if fig is not None else _plt.gcf()
        buf = _io.BytesIO()
        f.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        out({{
            "_image_png_b64": _b64.b64encode(buf.getvalue()).decode("ascii"),
            "title": title,
            "caption": caption,
        }})

    def read_artifact(_id):
        '''Load a prior artifact by id. Tables -> pandas DataFrame (or
        list-of-dict if pandas missing); images -> raw PNG bytes; text -> str.
        Only ids that appear literally in the script source are staged.'''
        import json as _json
        import os as _os
        _paths = _json.loads(_os.environ.get({_ART_PATHS_ENV!r}, "{{}}"))
        _path = _paths.get(_id)
        if _path is None:
            raise LookupError(
                f"artifact {{_id!r}} not staged; the runner only stages ids "
                f"that appear literally in the script source."
            )
        with open(_path, "r", encoding="utf-8") as _f:
            _meta = _json.load(_f)
        _kind = _meta.get("kind")
        _payload = _meta.get("payload") or {{}}
        if _kind == "table":
            try:
                import pandas as _pd
                return _pd.DataFrame(_payload.get("rows", []))
            except ImportError:
                return _payload.get("rows", [])
        if _kind == "image":
            import base64 as _b64
            return _b64.b64decode(_payload.get("data_b64", ""))
        if _kind == "text":
            return _payload.get("text", "")
        return _payload
    """
).strip()


async def _stage_artifacts_for_code(
    code: str,
) -> tuple[dict[str, str], Path | None]:
    ids = sorted(set(ARTIFACT_ID_RE.findall(code)))
    if not ids:
        return {}, None
    tmp = Path(tempfile.mkdtemp(prefix="lc_art_"))
    paths: dict[str, str] = {}
    for aid in ids:
        row = await get_artifact(aid)
        if row is None:
            continue
        path = tmp / f"{aid}.json"
        path.write_text(
            json.dumps(
                {
                    "id": row.id,
                    "kind": row.kind,
                    "title": row.title,
                    "payload": row.payload,
                }
            ),
            encoding="utf-8",
        )
        paths[aid] = str(path)
    if not paths:
        shutil.rmtree(tmp, ignore_errors=True)
        return {}, None
    return paths, tmp


async def run_python_artifact(code: str) -> dict[str, Any]:
    # Normalize before validation so the AST validator and the executor see
    # identical text (otherwise a leading-indent block would syntax-fail at
    # validate time but parse fine after dedent).
    code = textwrap.dedent(code)
    _validate_user_code(code)
    paths, tmp = await _stage_artifacts_for_code(code)
    try:
        return await asyncio.to_thread(_run_python_sync, code, paths)
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


_SAFE_ENV_KEYS = (
    "PATH",
    "SystemRoot",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
)

PY_OUTPUT_CAP_BYTES = 8 * 1024 * 1024
_TRUNCATED_MARKER = "\n[... output truncated; exceeded 8 MB cap ...]"


def _read_capped(p: Path) -> str:
    with p.open("rb") as f:
        data = f.read(PY_OUTPUT_CAP_BYTES + 1)
    truncated = len(data) > PY_OUTPUT_CAP_BYTES
    text = data[:PY_OUTPUT_CAP_BYTES].decode("utf-8", errors="replace")
    if truncated:
        text += _TRUNCATED_MARKER
    return text


def _run_python_sync(code: str, staged: dict[str, str]) -> dict[str, Any]:
    wrapped = _PY_PRELUDE + "\n" + code
    # Minimal env: subprocess inherits only what's needed to start Python.
    # Avoids leaking secrets (API keys, DB URLs, .env) to LLM-controlled code.
    env = {k: os.environ[k] for k in _SAFE_ENV_KEYS if k in os.environ}
    env[_ART_PATHS_ENV] = json.dumps(staged)
    env[_PROJECT_ROOT_ENV] = _PROJECT_ROOT
    if _FONT_DIR.is_dir():
        env[_FONT_DIR_ENV] = str(_FONT_DIR)
    # Per-run sandbox dir = subprocess cwd. Relative paths, matplotlib's
    # config cache (HOME/MPLCONFIGDIR), and tempfile.mkdtemp() inside user
    # code (TMPDIR/TEMP/TMP) all resolve here so unauthorized writes land
    # inside an ephemeral dir we wipe in the finally branch.
    sandbox_dir = tempfile.mkdtemp(prefix="lc_pyexec_")
    env["HOME"] = sandbox_dir
    env["MPLCONFIGDIR"] = sandbox_dir
    env["TMPDIR"] = sandbox_dir
    env["TEMP"] = sandbox_dir
    env["TMP"] = sandbox_dir
    # Redirect to disk-backed files instead of `capture_output=True` PIPEs:
    # PIPE buffers in our process memory unbounded, so a runaway `print(…)`
    # in LLM-authored code can OOM the API. RLIMIT_FSIZE in the preamble
    # caps each file at 50 MB in the subprocess, and we additionally cap
    # what we read back in-process below.
    stdout_path = Path(sandbox_dir) / ".stdout"
    stderr_path = Path(sandbox_dir) / ".stderr"
    try:
        with stdout_path.open("wb") as so, stderr_path.open("wb") as se:
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", wrapped],
                    stdout=so,
                    stderr=se,
                    timeout=PY_TIMEOUT_SECONDS,
                    check=False,
                    env=env,
                    cwd=sandbox_dir,
                )
            except subprocess.TimeoutExpired as err:
                raise TimeoutError(f"python_exec timed out after {PY_TIMEOUT_SECONDS}s") from err
        stdout = _read_capped(stdout_path)
        stderr = _read_capped(stderr_path)
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    if proc.returncode != 0:
        raise RuntimeError(f"python failed (exit {proc.returncode}):\n{stderr or stdout}")

    artifact_blob: Any | None = None
    free_stdout = stdout
    while ARTIFACT_START in free_stdout and ARTIFACT_END in free_stdout:
        a = free_stdout.index(ARTIFACT_START)
        b = free_stdout.index(ARTIFACT_END, a)
        body = free_stdout[a + len(ARTIFACT_START) : b]
        artifact_blob = json.loads(body)
        free_stdout = free_stdout[:a] + free_stdout[b + len(ARTIFACT_END) :]

    free_stdout = free_stdout.strip()

    return _classify_python_output(artifact_blob, free_stdout, stderr)


def _classify_python_output(blob: Any, free_stdout: str, stderr: str) -> dict[str, Any]:
    note = (free_stdout or "")[:400]
    if isinstance(blob, list) and blob and isinstance(blob[0], dict):
        cols = list(blob[0].keys())
        return {
            "kind": "table",
            "title": "Python result",
            "payload": {
                "columns": [{"key": c, "label": c} for c in cols],
                "rows": blob,
            },
            "summary": (
                f"table {len(blob)} rows x {len(cols)} cols ({', '.join(cols[:6])})"
                + (f"\n{note}" if note else "")
            ),
        }
    if isinstance(blob, dict) and "_image_png_b64" in blob:
        b64 = blob["_image_png_b64"]
        if not isinstance(b64, str):
            raise RuntimeError("out_image emitted non-string image payload")
        if len(b64) > 2 * 1024 * 1024:
            raise RuntimeError(
                f"image too large ({len(b64)} b64-bytes). Lower dpi or simplify the figure."
            )
        caption = blob.get("caption")
        return {
            "kind": "image",
            "title": blob.get("title") or "Python chart",
            "payload": {
                "format": "png",
                "data_b64": b64,
                "caption": caption,
            },
            "summary": (
                f"image png ({len(b64) * 3 // 4} bytes)" + (f" - {caption}" if caption else "")
            ),
        }
    if free_stdout:
        text = free_stdout
    elif isinstance(blob, str):
        text = blob
    elif blob is not None:
        text = json.dumps(blob)[:500]
    else:
        text = ""
    return {
        "kind": "text",
        "title": "Python output",
        "payload": {"text": text, "stderr": stderr.strip() or None},
        "summary": text[:400] if text else "(no output)",
    }


# ---------- SQL executor ----------

from sqlalchemy import event as _sa_event  # noqa: E402

_SQLITE_DENY = 1
_SQLITE_ATTACH = 24

_chinook_engine = None


def _chinook_path() -> Path:
    # Resolve to absolute so URI works regardless of CWD when the engine is built.
    p = Path(get_settings().chinook_db_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Chinook DB not found at {p}")
    return p


def _get_chinook_engine():
    global _chinook_engine  # noqa: PLW0603 -- module-level singleton, intentional
    if _chinook_engine is not None:
        return _chinook_engine
    # Read-only via URI; authorizer also blocks ATTACH so adversarial SQL
    # cannot pivot to other SQLite files (e.g. app.db, checkpoints.db).
    posix = _chinook_path().as_posix()
    uri = f"sqlite:///file:/{posix.lstrip('/')}?mode=ro&uri=true"
    engine = create_engine(uri, future=True)

    @_sa_event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _):
        def _authorizer(action, *_args):
            if action == _SQLITE_ATTACH:
                return _SQLITE_DENY
            return 0

        dbapi_conn.set_authorizer(_authorizer)

    _chinook_engine = engine
    return engine


async def run_sql_artifact(sql: str) -> dict[str, Any]:
    return await asyncio.to_thread(_run_sql_sync, sql)


def _run_sql_sync(sql: str) -> dict[str, Any]:
    engine = _get_chinook_engine()
    with engine.connect() as conn:
        cursor = conn.execute(text(sql))
        cols = list(cursor.keys())
        rows_iter = cursor.fetchmany(SQL_ROW_CAP + 1)
        truncated = len(rows_iter) > SQL_ROW_CAP
        rows = rows_iter[:SQL_ROW_CAP]
        out_rows = [
            {c: _coerce_cell(getattr(r, c, r[i])) for i, c in enumerate(cols)} for r in rows
        ]
    summary = f"sql {len(out_rows)} rows x {len(cols)} cols ({', '.join(cols[:6])})" + (
        " [truncated to 200]" if truncated else ""
    )
    return {
        "kind": "table",
        "title": "SQL result",
        "payload": {
            "columns": [{"key": c, "label": c} for c in cols],
            "rows": out_rows,
            "truncated": truncated,
        },
        "summary": summary,
    }


def _coerce_cell(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


# ---------- Persistence helpers used by streaming layer ----------


async def list_session_artifact_ids(session_id: str) -> list[str]:
    async with async_session() as s:
        rows = (
            await s.execute(select(SavedArtifact.id).where(SavedArtifact.session_id == session_id))
        ).all()
    return [r[0] for r in rows]


async def persist_tool_artifact(
    *,
    artifact: dict[str, Any],
    session_id: str | None,
    owner_id: str,
) -> SavedArtifact:
    """Called from streaming.py when a ToolMessage carries an `artifact` dict."""
    return await create_artifact(
        owner_id=owner_id,
        kind=artifact.get("kind", "text"),
        title=artifact.get("title", "Artifact"),
        payload=artifact.get("payload", {}),
        summary=artifact.get("summary", ""),
        source_kind=artifact.get("source_kind"),
        source_code=artifact.get("source_code"),
        parent_artifact_ids=artifact.get("parent_artifact_ids", []),
        session_id=session_id,
        artifact_id=artifact.get("id"),
    )


def session_id_from_config(config: RunnableConfig | None) -> str | None:
    return ((config or {}).get("configurable") or {}).get("thread_id")


def owner_id_from_config(config: RunnableConfig | None) -> str:
    owner_id = ((config or {}).get("configurable") or {}).get("owner_id")
    if not owner_id:
        raise RuntimeError("missing owner_id in RunnableConfig.configurable")
    return owner_id


async def build_and_persist_tool_artifact(
    *,
    result: dict[str, Any],
    source_kind: str,
    source_code: str,
    config: RunnableConfig | None,
    parent_artifact_ids: list[str] | None = None,
) -> tuple[str, dict]:
    artifact: dict[str, Any] = {
        "kind": result["kind"],
        "title": result["title"],
        "payload": result["payload"],
        "summary": result["summary"],
        "source_kind": source_kind,
        "source_code": source_code,
    }
    if parent_artifact_ids:
        artifact["parent_artifact_ids"] = parent_artifact_ids
    row = await persist_tool_artifact(
        artifact=artifact,
        session_id=session_id_from_config(config),
        owner_id=owner_id_from_config(config),
    )
    summary = f"{row.id} · {result['summary']}"
    if result.get("kind") == "table":
        from app.services.table_summary import build_compact_table_summary

        preview = build_compact_table_summary(row)
        if preview:
            summary = f"{summary}\n{preview}"
    return summary, {**artifact, "id": row.id}
