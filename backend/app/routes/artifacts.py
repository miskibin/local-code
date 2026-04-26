from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select
from app.db import async_session
from app.models import SavedArtifact

router = APIRouter()


class ArtifactDTO(BaseModel):
    id: str
    session_id: str | None = None
    kind: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/artifacts", response_model=list[ArtifactDTO])
async def list_artifacts():
    async with async_session() as s:
        rows = (await s.execute(select(SavedArtifact))).scalars().all()
    return [
        ArtifactDTO(
            id=r.id,
            session_id=r.session_id,
            kind=r.kind,
            title=r.title,
            payload=r.payload,
        )
        for r in rows
    ]


@router.post("/artifacts", response_model=ArtifactDTO)
async def upsert_artifact(dto: ArtifactDTO):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, dto.id)
        if existing is None:
            s.add(
                SavedArtifact(
                    id=dto.id,
                    session_id=dto.session_id,
                    kind=dto.kind,
                    title=dto.title,
                    payload=dto.payload,
                )
            )
        else:
            existing.session_id = dto.session_id
            existing.kind = dto.kind
            existing.title = dto.title
            existing.payload = dto.payload
        await s.commit()
    return dto


@router.delete("/artifacts/{aid}")
async def delete_artifact(aid: str):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, aid)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    return {"deleted": aid}
