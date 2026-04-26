from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from sqlmodel import select

from app.db import async_session
from app.models import ChatSession

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
async def get_messages(sid: str, request: Request):  # noqa: PLR0912 -- linear LC-message → UIPart conversion
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

        if not parts:
            continue
        out.append(
            UIMessage(
                id=getattr(m, "id", None) or f"m_{uuid4().hex}",
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
