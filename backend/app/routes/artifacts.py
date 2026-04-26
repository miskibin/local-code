from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from app.artifact_store import create_artifact, refresh_artifact
from app.db import async_session
from app.models import SavedArtifact

router = APIRouter()


class ArtifactDTO(BaseModel):
    id: str
    session_id: str | None = None
    kind: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    source_kind: str | None = None
    source_code: str | None = None
    parent_artifact_ids: list[str] = Field(default_factory=list)
    payload_size: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _to_dto(r: SavedArtifact) -> ArtifactDTO:
    return ArtifactDTO(
        id=r.id,
        session_id=r.session_id,
        kind=r.kind,
        title=r.title,
        payload=r.payload,
        summary=r.summary,
        source_kind=r.source_kind,
        source_code=r.source_code,
        parent_artifact_ids=list(r.parent_artifact_ids or []),
        payload_size=r.payload_size,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/artifacts", response_model=list[ArtifactDTO])
async def list_artifacts():
    async with async_session() as s:
        rows = (await s.execute(select(SavedArtifact))).scalars().all()
    return [_to_dto(r) for r in rows]


@router.get("/artifacts/{aid}", response_model=ArtifactDTO)
async def get_artifact_route(aid: str):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, aid)
    if existing is None:
        raise HTTPException(404)
    return _to_dto(existing)


@router.post("/artifacts", response_model=ArtifactDTO)
async def upsert_artifact(dto: ArtifactDTO):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, dto.id)
        if existing is None:
            row = await create_artifact(
                kind=dto.kind,
                title=dto.title,
                payload=dto.payload,
                summary=dto.summary,
                source_kind=dto.source_kind,
                source_code=dto.source_code,
                parent_artifact_ids=dto.parent_artifact_ids,
                session_id=dto.session_id,
                artifact_id=dto.id,
            )
            return _to_dto(row)
        existing.session_id = dto.session_id
        existing.kind = dto.kind
        existing.title = dto.title
        existing.payload = dto.payload
        existing.summary = dto.summary
        existing.source_kind = dto.source_kind
        existing.source_code = dto.source_code
        existing.parent_artifact_ids = list(dto.parent_artifact_ids or [])
        existing.updated_at = datetime.now(UTC)
        s.add(existing)
        await s.commit()
        await s.refresh(existing)
    return _to_dto(existing)


@router.post("/artifacts/{aid}/refresh", response_model=ArtifactDTO)
async def refresh_artifact_route(aid: str):
    try:
        row = await refresh_artifact(aid)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _to_dto(row)


@router.delete("/artifacts/{aid}")
async def delete_artifact(aid: str):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, aid)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    return {"deleted": aid}
