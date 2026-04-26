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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from sqlalchemy import create_engine, text
from sqlmodel import select

from app.config import get_settings
from app.db import async_session
from app.models import SavedArtifact

SOURCE_CODE_MAX = 64 * 1024
PAYLOAD_MAX_BYTES = 1 * 1024 * 1024
SQL_ROW_CAP = 200
PY_TIMEOUT_SECONDS = 20
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
        row.updated_at = _now()
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

import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

_ART_ID_PATTERN = re.compile(r"art_[0-9a-f]{8,}")
_ART_PATHS_ENV = "LC_ARTIFACT_PATHS"

_PY_PRELUDE = textwrap.dedent(
    f"""
    import json as _json, sys as _sys
    def out(_obj):
        _sys.stdout.write({ARTIFACT_START!r})
        _sys.stdout.write(_json.dumps(_obj, default=str))
        _sys.stdout.write({ARTIFACT_END!r})
        _sys.stdout.write("\\n")

    def out_image(fig=None, *, title=None, caption=None):
        import io as _io, base64 as _b64
        import matplotlib
        matplotlib.use("Agg")
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
    ids = sorted(set(_ART_ID_PATTERN.findall(code)))
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
    paths, tmp = await _stage_artifacts_for_code(code)
    try:
        return await asyncio.to_thread(_run_python_sync, code, paths)
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def _run_python_sync(code: str, staged: dict[str, str]) -> dict[str, Any]:
    wrapped = _PY_PRELUDE + "\n" + textwrap.dedent(code)
    env = os.environ.copy()
    env[_ART_PATHS_ENV] = json.dumps(staged)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", wrapped],
            capture_output=True,
            timeout=PY_TIMEOUT_SECONDS,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as err:
        raise TimeoutError(f"python_exec timed out after {PY_TIMEOUT_SECONDS}s") from err

    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    if proc.returncode != 0:
        raise RuntimeError(f"python failed (exit {proc.returncode}):\n{stderr or stdout}")

    artifact_blob: Any | None = None
    free_stdout = stdout
    while ARTIFACT_START in free_stdout and ARTIFACT_END in free_stdout:
        a = free_stdout.index(ARTIFACT_START)
        b = free_stdout.index(ARTIFACT_END, a)
        body = free_stdout[a + len(ARTIFACT_START) : b]
        try:
            artifact_blob = json.loads(body)
        except json.JSONDecodeError:
            artifact_blob = None
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
    text = free_stdout if free_stdout else (json.dumps(blob)[:500] if blob is not None else "")
    return {
        "kind": "text",
        "title": "Python output",
        "payload": {"text": text, "stderr": stderr.strip() or None},
        "summary": text[:400] if text else "(no output)",
    }


# ---------- SQL executor ----------


def _chinook_path() -> str:
    p = Path(get_settings().chinook_db_path)
    if not p.exists():
        raise FileNotFoundError(f"Chinook DB not found at {p}")
    return str(p)


async def run_sql_artifact(sql: str) -> dict[str, Any]:
    return await asyncio.to_thread(_run_sql_sync, sql)


def _run_sql_sync(sql: str) -> dict[str, Any]:
    engine = create_engine(f"sqlite:///{_chinook_path()}", future=True)
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
    return summary, {**artifact, "id": row.id}
