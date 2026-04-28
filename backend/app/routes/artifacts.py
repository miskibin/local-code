import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import select

from app.artifact_store import create_artifact, refresh_artifact
from app.auth import CurrentUser
from app.config import get_settings
from app.db import async_session
from app.models import SavedArtifact
from app.services.table_summary import summarize_csv

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
    pinned: bool = False
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
        pinned=bool(r.pinned),
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/artifacts", response_model=list[ArtifactDTO])
async def list_artifacts(user: CurrentUser, pinned: bool | None = None):
    async with async_session() as s:
        stmt = select(SavedArtifact).where(SavedArtifact.owner_id == user.id)
        if pinned is not None:
            stmt = stmt.where(SavedArtifact.pinned == pinned)
        rows = (await s.execute(stmt)).scalars().all()
    return [_to_dto(r) for r in rows]


@router.get("/artifacts/{aid}", response_model=ArtifactDTO)
async def get_artifact_route(aid: str):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, aid)
    if existing is None:
        raise HTTPException(404)
    return _to_dto(existing)


@router.post("/artifacts", response_model=ArtifactDTO)
async def upsert_artifact(dto: ArtifactDTO, user: CurrentUser):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, dto.id)
        if existing is None:
            await create_artifact(
                owner_id=user.id,
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
            fresh = await s.get(SavedArtifact, dto.id)
            assert fresh is not None
            fresh.pinned = True
            s.add(fresh)
            await s.commit()
            await s.refresh(fresh)
            return _to_dto(fresh)
        existing.session_id = dto.session_id
        existing.kind = dto.kind
        existing.title = dto.title
        existing.payload = dto.payload
        existing.summary = dto.summary
        existing.source_kind = dto.source_kind
        existing.source_code = dto.source_code
        existing.parent_artifact_ids = list(dto.parent_artifact_ids or [])
        existing.pinned = True
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


_TABLE_MIME = {"text/csv", "application/csv", "text/tab-separated-values"}
_TABLE_EXT = {".csv", ".tsv"}
_TEXT_PREFIXES = ("text/",)


def _resolve_mime(filename: str | None, declared: str | None) -> str:
    if declared and declared != "application/octet-stream":
        return declared
    if filename:
        guess, _ = mimetypes.guess_type(filename)
        if guess:
            return guess
    return "application/octet-stream"


def _classify(filename: str, mime: str) -> str:
    ext = Path(filename).suffix.lower()
    if mime.startswith("image/"):
        return "image"
    if mime in _TABLE_MIME or ext in _TABLE_EXT:
        return "table"
    if mime.startswith(_TEXT_PREFIXES):
        return "text"
    return "unsupported"


@router.post("/artifacts/upload", response_model=ArtifactDTO)
async def upload_artifact(
    file: UploadFile,
    user: CurrentUser,
    session_id: str | None = Form(default=None),
):
    name = file.filename or "upload"
    mime = _resolve_mime(name, file.content_type)
    kind = _classify(name, mime)
    if kind == "unsupported":
        raise HTTPException(415, f"unsupported upload type: {mime} ({name})")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    body = await file.read()
    size = len(body)
    suffix = Path(name).suffix or ""

    aid = f"art_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    path = uploads_dir / f"{aid}{suffix}"
    path.write_bytes(body)

    payload: dict[str, Any] = {"path": str(path), "mime": mime, "size": size, "filename": name}
    summary = ""
    title = name

    if kind == "table":
        try:
            meta = summarize_csv(path, artifact_id=aid, title=name)
        except (
            pd.errors.ParserError,
            pd.errors.EmptyDataError,
            UnicodeDecodeError,
            ValueError,
            OSError,
        ) as e:
            logger.exception("csv summary failed")
            raise HTTPException(400, f"failed to parse table: {e}") from e
        payload.update(meta)
        summary = f"{meta['n_rows']} rows × {meta['n_cols']} cols"  # noqa: RUF001
    elif kind == "image":
        summary = f"image {mime}, {size} bytes"
    else:  # text
        try:
            preview = body.decode("utf-8", errors="replace")[:500]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"text preview decode failed: {type(e).__name__}: {e}")
            preview = ""
        payload["text_preview"] = preview
        summary = f"text {size} bytes"

    row = await create_artifact(
        owner_id=user.id,
        kind=kind,
        title=title,
        payload=payload,
        summary=summary,
        source_kind="upload",
        source_code=None,
        session_id=session_id,
        artifact_id=aid,
    )
    logger.info(f"upload artifact id={row.id} kind={kind} mime={mime} size={size}")
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


@router.get("/artifacts/{aid}/file")
async def download_artifact_file(aid: str):
    async with async_session() as s:
        existing = await s.get(SavedArtifact, aid)
    if existing is None:
        raise HTTPException(404, "artifact not found")
    payload = existing.payload or {}
    raw_path = payload.get("path")
    if not raw_path:
        raise HTTPException(404, "artifact has no file payload")
    file_path = Path(raw_path)
    if not file_path.is_file():
        raise HTTPException(404, "file missing on disk")
    filename = payload.get("filename") or file_path.name
    media = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if existing.kind != "pptx":
        media = payload.get("mime") or "application/octet-stream"
    return FileResponse(str(file_path), filename=filename, media_type=media)
