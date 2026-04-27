import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from sqlmodel import select

from app.artifact_store import get_artifact
from app.config import get_settings
from app.db import async_session
from app.models import ChatSession, MessageTrace

_ART_DOT_PREFIX = re.compile(r"^\s*(art_[A-Za-z0-9]+)\s*·")

router = APIRouter()


class SessionDTO(BaseModel):
    id: str
    title: str = ""
    is_pinned: bool = False


class SessionPatch(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None


class UIMessage(BaseModel):
    id: str
    role: str
    parts: list[dict[str, Any]]


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(str(c.get("text", "")))
            elif isinstance(c, str):
                out.append(c)
        return "".join(out)
    return ""


def _coerce_output(content) -> object:
    if isinstance(content, (str, int, float, bool)) or content is None:
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(str(c.get("text", "")))
            else:
                parts.append(str(c))
        return "".join(parts)
    return str(content)


def _artifact_id_from_tool_message(tm: Any) -> str | None:
    """Recover artifact id from checkpoint ToolMessage (live SSE adds data-artifact separately)."""
    raw = getattr(tm, "content", None)
    if isinstance(raw, dict):
        for key in ("artifact_id", "artifactId"):
            v = raw.get(key)
            if isinstance(v, str) and v.startswith("art_"):
                return v
        art = raw.get("artifact")
        if isinstance(art, dict):
            vid = art.get("id")
            if isinstance(vid, str):
                return vid
    coerced = _coerce_output(raw)
    if isinstance(coerced, str):
        text = coerced.strip()
        m = _ART_DOT_PREFIX.match(text)
        if m:
            return m.group(1)
        if text.startswith("{"):
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict):
                v = obj.get("artifact_id") or obj.get("artifactId")
                if isinstance(v, str):
                    return v
        m2 = re.search(r"\b(art_[A-Za-z0-9]+)\b", text)
        if m2:
            return m2.group(1)
    return None


@router.get("/sessions", response_model=list[SessionDTO])
async def list_sessions():
    async with async_session() as s:
        rows = (
            (
                await s.execute(
                    select(ChatSession).order_by(
                        ChatSession.is_pinned.desc(),
                        ChatSession.pinned_at.desc().nullslast(),
                        ChatSession.created_at.desc(),
                    )
                )
            )
            .scalars()
            .all()
        )
    return [SessionDTO(id=r.id, title=r.title, is_pinned=bool(r.is_pinned)) for r in rows]


@router.post("/sessions", response_model=SessionDTO)
async def create_session(dto: SessionDTO):
    async with async_session() as s:
        if await s.get(ChatSession, dto.id):
            return dto
        s.add(ChatSession(id=dto.id, title=dto.title))
        await s.commit()
    return dto


@router.patch("/sessions/{sid}", response_model=SessionDTO)
async def patch_session(sid: str, patch: SessionPatch):
    async with async_session() as s:
        row = await s.get(ChatSession, sid)
        if row is None:
            raise HTTPException(404)
        if patch.title is not None:
            row.title = patch.title
        if patch.is_pinned is not None:
            row.is_pinned = patch.is_pinned
            row.pinned_at = datetime.now(UTC) if patch.is_pinned else None
        s.add(row)
        await s.commit()
        await s.refresh(row)
    return SessionDTO(id=row.id, title=row.title, is_pinned=bool(row.is_pinned))


@router.get("/sessions/{sid}/messages", response_model=list[UIMessage])
async def get_messages(sid: str, request: Request):  # noqa: PLR0912, PLR0915 -- linear LC-message → UIPart conversion
    cp = request.app.state.checkpointer
    tup = await cp.aget_tuple({"configurable": {"thread_id": sid}})
    if tup is None:
        return []
    msgs = tup.checkpoint.get("channel_values", {}).get("messages", []) or []

    # Pre-index ToolMessages by tool_call_id so AIMessage tool_calls can be
    # rendered with their matching output state on reload.
    tool_outputs: dict[str, Any] = {}
    for m in msgs:
        if m.type == "tool":
            cid = getattr(m, "tool_call_id", None)
            if cid:
                tool_outputs[cid] = m

    async with async_session() as s:
        rows = (
            await s.execute(select(MessageTrace).where(MessageTrace.session_id == sid))
        ).scalars().all()
    traces_by_msg_id: dict[str, str] = {r.ai_message_id: r.trace_id for r in rows}

    feedback_by_trace: dict[str, int] = {}
    trace_url_by_id: dict[str, str] = {}
    if traces_by_msg_id and get_settings().langfuse_secret_key:
        from langfuse import get_client

        client = get_client()
        scores = client.api.scores.get_many(
            session_id=sid, name="user-feedback", limit=100
        )
        for sc in getattr(scores, "data", []) or []:
            tid = getattr(sc, "trace_id", None)
            val = getattr(sc, "value", None)
            if tid and val is not None and tid not in feedback_by_trace:
                feedback_by_trace[tid] = int(val)
        for tid in set(traces_by_msg_id.values()):
            trace_url_by_id[tid] = client.get_trace_url(trace_id=tid)

    out: list[UIMessage] = []
    for m in msgs:
        if m.type == "human":
            text_content = _extract_text(m.content)
            if not text_content:
                continue
            out.append(
                UIMessage(
                    id=getattr(m, "id", None) or f"m_{uuid4().hex}",
                    role="user",
                    parts=[{"type": "text", "text": text_content}],
                )
            )
            continue

        if m.type != "ai":
            continue

        parts: list[dict[str, Any]] = []
        text_content = _extract_text(m.content)
        if text_content:
            parts.append({"type": "text", "text": text_content})

        for tc in getattr(m, "tool_calls", None) or []:
            cid = tc.get("id")
            if not cid:
                continue
            name = tc.get("name") or "tool"
            args = tc.get("args") or {}
            part: dict[str, Any] = {
                "type": f"tool-{name}",
                "toolCallId": cid,
                "toolName": name,
                "input": args,
            }
            tm = tool_outputs.get(cid)
            if tm is None:
                part["state"] = "input-available"
            else:
                output = _coerce_output(tm.content)
                if getattr(tm, "status", None) == "error":
                    part["state"] = "output-error"
                    part["errorText"] = str(output)
                else:
                    part["state"] = "output-available"
                    part["output"] = output
            parts.append(part)
            if (
                tm is not None
                and getattr(tm, "status", None) != "error"
                and part.get("state") == "output-available"
            ):
                aid = _artifact_id_from_tool_message(tm)
                if aid:
                    row = await get_artifact(aid)
                    if row is not None and (
                        row.session_id is None or row.session_id == sid
                    ):
                        parts.append(
                            {
                                "type": "data-artifact",
                                "id": row.id,
                                "data": {
                                    "toolCallId": cid,
                                    "artifactId": row.id,
                                    "kind": row.kind,
                                    "title": row.title,
                                    "summary": row.summary,
                                    "updatedAt": row.updated_at.isoformat(),
                                },
                            }
                        )

        umd = getattr(m, "usage_metadata", None)
        if isinstance(umd, dict) and (
            umd.get("input_tokens") or umd.get("output_tokens")
        ):
            parts.append(
                {
                    "type": "data-usage",
                    "id": f"usage_{getattr(m, 'id', None) or uuid4().hex}",
                    "data": {
                        "inputTokens": int(umd.get("input_tokens") or 0),
                        "outputTokens": int(umd.get("output_tokens") or 0),
                    },
                }
            )

        m_id = getattr(m, "id", None)
        if m_id and m_id in traces_by_msg_id:
            tid = traces_by_msg_id[m_id]
            data: dict[str, Any] = {"traceId": tid, "messageId": m_id}
            if tid in trace_url_by_id:
                data["traceUrl"] = trace_url_by_id[tid]
            if tid in feedback_by_trace:
                data["feedback"] = feedback_by_trace[tid]
            parts.append(
                {
                    "type": "data-trace",
                    "id": f"trace_{m_id}",
                    "data": data,
                }
            )

        if not parts:
            continue
        out.append(
            UIMessage(
                id=m_id or f"m_{uuid4().hex}",
                role="assistant",
                parts=parts,
            )
        )
    return out


@router.delete("/sessions/{sid}")
async def delete_session(sid: str):
    async with async_session() as s:
        existing = await s.get(ChatSession, sid)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    logger.info(f"session delete {sid}")
    return {"deleted": sid}
