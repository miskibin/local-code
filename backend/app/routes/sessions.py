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


class UIPart(BaseModel):
    type: str
    text: str


class UIMessage(BaseModel):
    id: str
    role: str
    parts: list[UIPart]


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


@router.get("/sessions", response_model=list[SessionDTO])
async def list_sessions():
    async with async_session() as s:
        rows = (
            await s.execute(select(ChatSession).order_by(ChatSession.created_at.desc()))
        ).scalars().all()
    return [SessionDTO(id=r.id, title=r.title) for r in rows]


@router.post("/sessions", response_model=SessionDTO)
async def create_session(dto: SessionDTO):
    async with async_session() as s:
        if await s.get(ChatSession, dto.id):
            return dto
        s.add(ChatSession(id=dto.id, title=dto.title))
        await s.commit()
    return dto


@router.get("/sessions/{sid}/messages", response_model=list[UIMessage])
async def get_messages(sid: str, request: Request):
    cp = request.app.state.checkpointer
    tup = await cp.aget_tuple({"configurable": {"thread_id": sid}})
    if tup is None:
        return []
    msgs = tup.checkpoint.get("channel_values", {}).get("messages", []) or []
    out: list[UIMessage] = []
    for m in msgs:
        role = "user" if m.type == "human" else "assistant" if m.type == "ai" else None
        if role is None:
            continue
        text = _extract_text(m.content)
        if not text:
            continue
        out.append(
            UIMessage(
                id=getattr(m, "id", None) or f"m_{uuid4().hex}",
                role=role,
                parts=[UIPart(type="text", text=text)],
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
