"""Persistence helpers for SavedTask. Same pattern as artifact_store."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import select

from app.db import async_session
from app.models import SavedTask
from app.tasks.schemas import TaskDTO


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return f"tsk_{uuid4().hex[:12]}"


def to_dto(row: SavedTask) -> TaskDTO:
    return TaskDTO.model_validate(
        {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "source_session_id": row.source_session_id,
            "variables": row.variables,
            "steps": row.steps,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


def to_row(dto: TaskDTO) -> SavedTask:
    now = _now()
    return SavedTask(
        id=dto.id or _new_id(),
        title=dto.title,
        description=dto.description,
        source_session_id=dto.source_session_id,
        variables=[v.model_dump() for v in dto.variables],
        steps=[s.model_dump() for s in dto.steps],
        created_at=dto.created_at or now,
        updated_at=now,
    )


async def list_tasks() -> list[SavedTask]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(SavedTask).order_by(SavedTask.updated_at.desc())))
            .scalars()
            .all()
        )
    return list(rows)


async def get_task(task_id: str) -> SavedTask | None:
    async with async_session() as s:
        return await s.get(SavedTask, task_id)


async def upsert_task(dto: TaskDTO) -> SavedTask:
    async with async_session() as s:
        existing = await s.get(SavedTask, dto.id) if dto.id else None
        if existing is None:
            row = to_row(dto)
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return row
        existing.title = dto.title
        existing.description = dto.description
        existing.source_session_id = dto.source_session_id
        existing.variables = [v.model_dump() for v in dto.variables]
        existing.steps = [s_.model_dump() for s_ in dto.steps]
        existing.updated_at = _now()
        s.add(existing)
        await s.commit()
        await s.refresh(existing)
        return existing


async def delete_task(task_id: str) -> bool:
    async with async_session() as s:
        existing = await s.get(SavedTask, task_id)
        if existing is None:
            return False
        await s.delete(existing)
        await s.commit()
    return True


async def create_task(dto: TaskDTO) -> SavedTask:
    """Always insert a new row with a fresh id (used by /generate and /import)."""
    payload = dto.model_copy(update={"id": _new_id()})
    return await upsert_task(payload)
