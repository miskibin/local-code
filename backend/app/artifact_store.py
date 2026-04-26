"""Single source of truth for artifact creation, hydration, and refresh.

Tools and the /artifacts/{id}/refresh route both go through here so write paths
stay in one place. Per-kind executors live below; pick one via `source_kind`.
"""

from __future__ import annotations

import asyncio
import json
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger
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
        result = await _run_executor(
            row.source_kind,
            row.source_code,
            parent_artifact_ids=list(row.parent_artifact_ids or []),
        )
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
    if source_kind == "chart":
        spec = json.loads(source_code)
        if parent_artifact_ids:
            spec["artifact_id"] = parent_artifact_ids[0]
        return await run_chart_artifact(spec)
    if source_kind == "text":
        return {
            "kind": "text",
            "title": "Text",
            "payload": {"text": source_code},
            "summary": source_code.splitlines()[0][:200] if source_code else "",
        }
    raise ValueError(f"unknown source_kind: {source_kind}")


# ---------- Python executor ----------

_PY_PRELUDE = textwrap.dedent(
    f"""
    import json as _json, sys as _sys
    def out(_obj):
        _sys.stdout.write({ARTIFACT_START!r})
        _sys.stdout.write(_json.dumps(_obj, default=str))
        _sys.stdout.write({ARTIFACT_END!r})
        _sys.stdout.write("\\n")
    """
).strip()


async def run_python_artifact(code: str) -> dict[str, Any]:
    return await asyncio.to_thread(_run_python_sync, code)


def _run_python_sync(code: str) -> dict[str, Any]:
    import subprocess

    wrapped = _PY_PRELUDE + "\n" + textwrap.dedent(code)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", wrapped],
            capture_output=True,
            timeout=PY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"python_exec timed out after {PY_TIMEOUT_SECONDS}s")

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


def _classify_python_output(
    blob: Any, free_stdout: str, stderr: str
) -> dict[str, Any]:
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
                f"table {len(blob)} rows × {len(cols)} cols ({', '.join(cols[:6])})"
                + (f"\n{note}" if note else "")
            ),
        }
    if (
        isinstance(blob, dict)
        and isinstance(blob.get("labels"), list)
        and isinstance(blob.get("values"), list)
    ):
        labels = blob["labels"]
        values = blob["values"]
        data = [
            {"label": str(lbl), "value": float(v)}
            for lbl, v in zip(labels, values, strict=False)
        ]
        return {
            "kind": "chart",
            "title": blob.get("title", "Python chart"),
            "payload": {"data": data, "caption": blob.get("caption")},
            "summary": f"chart {len(data)} points (range "
            f"{min(v for v in values):.2f}–{max(v for v in values):.2f})"
            + (f"\n{note}" if note else ""),
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
            {c: _coerce_cell(getattr(r, c, r[i])) for i, c in enumerate(cols)}
            for r in rows
        ]
    summary = (
        f"sql {len(out_rows)} rows × {len(cols)} cols ({', '.join(cols[:6])})"
        + (" [truncated to 200]" if truncated else "")
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


# ---------- Chart executor ----------


async def run_chart_artifact(spec: dict[str, Any]) -> dict[str, Any]:
    artifact_id = spec.get("artifact_id")
    x = spec.get("x")
    y = spec.get("y")
    kind = spec.get("kind", "bar")
    title = spec.get("title", "Chart")
    if not artifact_id or not x or not y:
        raise ValueError("chart spec requires artifact_id, x, y")
    src = await get_artifact(artifact_id)
    if src is None:
        raise LookupError(f"chart input artifact {artifact_id} not found")
    if src.kind != "table":
        raise ValueError(f"chart input must be a table artifact, got {src.kind}")
    rows = src.payload.get("rows", [])
    cols = {c["key"] for c in src.payload.get("columns", [])}
    if x not in cols or y not in cols:
        raise ValueError(
            f"chart fields {x!r}/{y!r} not in input columns {sorted(cols)}"
        )
    data = []
    for r in rows:
        try:
            data.append({"label": str(r[x]), "value": float(r[y])})
        except (TypeError, ValueError):
            logger.debug("skipping non-numeric chart row {} for y={}", r, y)
    summary = (
        f"chart kind={kind} {len(data)} points "
        f"(range {min((d['value'] for d in data), default=0):.2f}–"
        f"{max((d['value'] for d in data), default=0):.2f})"
    )
    return {
        "kind": "chart",
        "title": title,
        "payload": {"data": data, "caption": f"{kind}: {y} by {x}"},
        "summary": summary,
    }


# ---------- Persistence helpers used by streaming layer ----------


async def list_session_artifact_ids(session_id: str) -> list[str]:
    async with async_session() as s:
        rows = (
            await s.execute(
                select(SavedArtifact.id).where(SavedArtifact.session_id == session_id)
            )
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
