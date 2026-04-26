from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from app.db import async_session
from app.models import ChatSession

router = APIRouter()


class SessionDTO(BaseModel):
    id: str
    title: str = ""


@router.get("/sessions", response_model=list[SessionDTO])
async def list_sessions():
    async with async_session() as s:
        rows = (await s.execute(select(ChatSession))).scalars().all()
    return [SessionDTO(id=r.id, title=r.title) for r in rows]


@router.post("/sessions", response_model=SessionDTO)
async def create_session(dto: SessionDTO):
    async with async_session() as s:
        if await s.get(ChatSession, dto.id):
            return dto
        s.add(ChatSession(id=dto.id, title=dto.title))
        await s.commit()
    return dto


@router.delete("/sessions/{sid}")
async def delete_session(sid: str):
    async with async_session() as s:
        existing = await s.get(ChatSession, sid)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    return {"deleted": sid}
