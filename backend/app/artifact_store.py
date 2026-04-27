"""Single source of truth for artifact creation, hydration, and refresh.

Tools and the /artifacts/{id}/refresh route both go through here so write paths
stay in one place. Per-kind executors live below; pick one via `source_kind`.
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from loguru import logger
from sqlalchemy import create_engine, text
from sqlmodel import select

from app.config import get_settings
from app.db import async_session
from app.models import SavedArtifact

if TYPE_CHECKING:
    from langchain_sandbox import PyodideSandbox

SOURCE_CODE_MAX = 64 * 1024
PAYLOAD_MAX_BYTES = 1 * 1024 * 1024
SQL_ROW_CAP = 200
STDOUT_CAP_BYTES = 1 * 1024 * 1024
ARTIFACT_START = "<<ARTIFACT::start>>"
ARTIFACT_END = "<<ARTIFACT::end>>"


def _now() -> datetime:
    return datetime.now(UTC)


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
    now = _now()
    row = SavedArtifact(
        id=aid,
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


async def refresh_artifact(
    artifact_id: str,
    *,
    sandbox: "PyodideSandbox | None" = None,
) -> SavedArtifact:
    async with async_session() as s:
        row = await s.get(SavedArtifact, artifact_id)
        if row is None:
            raise LookupError(f"artifact {artifact_id} not found")
        if not row.source_kind or row.source_code is None:
            raise ValueError(f"artifact {artifact_id} has no source to refresh")
        source_kind = row.source_kind
        source_code = row.source_code
        parent_ids = list(row.parent_artifact_ids or [])
        # Refresh runs without an attached chat thread — use a stable per-artifact
        # session so re-running a refresh keeps the same Python globals.
        refresh_session_id = f"refresh_{artifact_id}"

    result = await _run_executor(
        source_kind,
        source_code,
        parent_artifact_ids=parent_ids,
        sandbox=sandbox,
        session_id=refresh_session_id,
    )

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
        row.updated_at = _now()
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row


async def _run_executor(
    source_kind: str,
    source_code: str,
    parent_artifact_ids: list[str],
    *,
    sandbox: "PyodideSandbox | None" = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    if source_kind == "python":
        if sandbox is None:
            raise RuntimeError("python executor requires sandbox")
        return await run_python_artifact(source_code, sandbox=sandbox, session_id=session_id)
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

import re  # noqa: E402

_ART_ID_PATTERN = re.compile(r"art_[0-9a-f]{8,}")

_PY_PRELUDE_TEMPLATE = textwrap.dedent(
    f"""
    import json as _json, sys as _sys
    _STAGED = _json.loads({{staged_literal}})

    # Pre-import the scientific stack at the TOP LEVEL so the wrapper's
    # find_imports picks them up and install_imports() resolves them via
    # micropip ONCE per session. Without these imports, user code like
    # `import matplotlib.pyplot as plt` would surface as
    # `matplotlib.pyplot` to install_imports — which then tries to fetch
    # a non-existent `matplotlib-pyplot` package from PyPI and fails.
    # Top-level `import matplotlib` instead loads the real package; the
    # submodule import in user code becomes a no-op resolution against
    # already-loaded matplotlib.
    try:
        import matplotlib as _bootstrap_mpl  # noqa: F401
    except ImportError:
        pass
    try:
        import numpy as _bootstrap_np  # noqa: F401
    except ImportError:
        pass
    try:
        import pandas as _bootstrap_pd  # noqa: F401
    except ImportError:
        pass

    def out(_obj):
        _sys.stdout.write({ARTIFACT_START!r})
        _sys.stdout.write(_json.dumps(_obj, default=str))
        _sys.stdout.write({ARTIFACT_END!r})
        _sys.stdout.write("\\n")

    def _apply_app_mpl_style():
        # Imports go through importlib.import_module rather than top-level
        # `import matplotlib` so that the sandbox wrapper's `find_imports` AST
        # scan doesn't try to micropip-install matplotlib on every call.
        # matplotlib loads lazily when the agent first calls out_image().
        import importlib as _imp
        _mpl = _imp.import_module("matplotlib")
        _mpl.use("Agg")
        _cycler = _imp.import_module("cycler").cycler
        _ink_text = "#1f1f1f"
        _ink_spine = "#6b6b6b"
        _grid = "#c8c8c8"
        _mpl.rcParams.update({{{{
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
            "legend.frameon": False,
            "legend.fontsize": 10,
            "legend.labelcolor": _ink_text,
            "savefig.facecolor": "none",
            "savefig.edgecolor": "none",
            "savefig.transparent": True,
        }}}})

    def out_image(fig=None, *, title=None, caption=None):
        import io as _io, base64 as _b64, importlib as _imp
        if "_app_mpl_style_applied" not in globals():
            _apply_app_mpl_style()
            globals()["_app_mpl_style_applied"] = True
        _plt = _imp.import_module("matplotlib.pyplot")
        f = fig if fig is not None else _plt.gcf()
        buf = _io.BytesIO()
        f.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        out({{{{
            "_image_png_b64": _b64.b64encode(buf.getvalue()).decode("ascii"),
            "title": title,
            "caption": caption,
        }}}})

    def read_artifact(_id):
        '''Load a prior artifact by id (literal in script source). Tables ->
        pandas DataFrame; images -> raw PNG bytes; text -> str.'''
        _meta = _STAGED.get(_id)
        if _meta is None:
            raise LookupError(
                f"artifact {{{{_id!r}}}} not staged; the runner only stages ids "
                f"that appear literally in the script source."
            )
        _kind = _meta.get("kind")
        _payload = _meta.get("payload") or {{{{}}}}
        if _kind == "table":
            try:
                import importlib as _imp
                _pd = _imp.import_module("pandas")
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


async def _stage_artifacts_for_code(code: str) -> dict[str, dict[str, Any]]:
    """Resolve `art_<hex>` literals in the script and return id -> metadata.

    Pyodide has no host filesystem, so artifacts are inlined as a JSON literal
    in the prelude (see _PY_PRELUDE_TEMPLATE) instead of being written to a
    tempdir + read via env var as we did under the old subprocess executor.
    """
    ids = sorted(set(_ART_ID_PATTERN.findall(code)))
    if not ids:
        return {}
    staged: dict[str, dict[str, Any]] = {}
    for aid in ids:
        row = await get_artifact(aid)
        if row is None:
            continue
        staged[aid] = {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "payload": row.payload,
        }
    return staged


async def run_python_artifact(
    code: str,
    *,
    sandbox: "PyodideSandbox",
    session_id: str | None = None,
) -> dict[str, Any]:
    staged = await _stage_artifacts_for_code(code)
    # JSON-encode the staged dict to a Python literal expression. We embed it
    # via `json.loads(<literal>)` in the prelude rather than building a Python
    # dict at the source level so we don't have to think about escaping.
    staged_literal = repr(json.dumps(staged))
    prelude = _PY_PRELUDE_TEMPLATE.format(staged_literal=staged_literal)
    wrapped = prelude + "\n" + textwrap.dedent(code)

    from app.python_sandbox import execute_code

    timeout = get_settings().python_sandbox_timeout
    try:
        result = await asyncio.wait_for(
            execute_code(sandbox, wrapped, session_id=session_id, timeout_seconds=timeout),
            timeout=timeout + 5,
        )
    except TimeoutError as err:
        raise TimeoutError(f"python_exec timed out after {timeout}s") from err

    stdout = (result.stdout or "")[:STDOUT_CAP_BYTES]
    stderr = (result.stderr or "")[:STDOUT_CAP_BYTES]
    if result.status != "success":
        # When status=="error" stdout/stderr may be empty (Pyodide failed
        # before user code ran); surface whichever non-empty channel we have.
        msg = stderr or stdout or "python_exec failed (no output)"
        logger.warning(f"python_exec failed: {msg[:200]}")
        raise RuntimeError(msg)

    artifact_blob: Any | None = None
    free_stdout = stdout
    while ARTIFACT_START in free_stdout and ARTIFACT_END in free_stdout:
        a = free_stdout.index(ARTIFACT_START)
        b = free_stdout.index(ARTIFACT_END, a)
        body = free_stdout[a + len(ARTIFACT_START) : b]
        artifact_blob = json.loads(body)
        free_stdout = free_stdout[:a] + free_stdout[b + len(ARTIFACT_END) :]

    # Pyodide's loadPackage() prints "Loading X" / "Loaded X" lines to stdout
    # the first time a package is imported in a session. Filter them so the
    # agent's text artifact only shows code-produced output.
    cleaned_lines = [
        ln
        for ln in free_stdout.splitlines()
        if not (ln.startswith("Loading ") or ln.startswith("Loaded "))
    ]
    free_stdout = "\n".join(cleaned_lines).strip()

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
    text = free_stdout if free_stdout else (json.dumps(blob)[:500] if blob is not None else "")
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
) -> SavedArtifact:
    """Called from streaming.py when a ToolMessage carries an `artifact` dict."""
    return await create_artifact(
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
    row = await persist_tool_artifact(artifact=artifact, session_id=session_id_from_config(config))
    summary = f"{row.id} · {result['summary']}"
    if result.get("kind") == "table":
        from app.services.table_summary import build_compact_table_summary

        preview = build_compact_table_summary(row)
        if preview:
            summary = f"{summary}\n{preview}"
    return summary, {**artifact, "id": row.id}
