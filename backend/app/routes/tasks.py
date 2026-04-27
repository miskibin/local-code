from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from app.llm import resolve_llm
from app.tasks.generator import generate_task_from_run
from app.tasks.schemas import (
    GenerateTaskRequest,
    TaskDTO,
    TaskListItem,
)
from app.tasks.storage import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    to_dto,
    upsert_task,
)

router = APIRouter()


@router.get("/tasks", response_model=list[TaskListItem])
async def list_tasks_route():
    rows = await list_tasks()
    return [
        TaskListItem(
            id=r.id,
            title=r.title,
            description=r.description,
            tags=r.tags or [],
            role=r.role,
            creator=r.creator,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/tasks/{tid}", response_model=TaskDTO)
async def get_task_route(tid: str):
    row = await get_task(tid)
    if row is None:
        raise HTTPException(404)
    return to_dto(row)


@router.put("/tasks/{tid}", response_model=TaskDTO)
async def update_task_route(tid: str, dto: TaskDTO):
    existing = await get_task(tid)
    if existing is None:
        raise HTTPException(404)
    payload = dto.model_copy(update={"id": tid})
    row = await upsert_task(payload)
    return to_dto(row)


@router.delete("/tasks/{tid}")
async def delete_task_route(tid: str):
    deleted = await delete_task(tid)
    if not deleted:
        raise HTTPException(404)
    return {"deleted": tid}


@router.get("/tasks/{tid}/export", response_model=TaskDTO)
async def export_task_route(tid: str):
    row = await get_task(tid)
    if row is None:
        raise HTTPException(404)
    dto = to_dto(row)
    # Export strips identifiers / timestamps so import always creates fresh ids.
    return dto.model_copy(
        update={
            "id": "",
            "source_session_id": None,
            "created_at": None,
            "updated_at": None,
        }
    )


@router.post("/tasks/import", response_model=TaskDTO)
async def import_task_route(dto: TaskDTO):
    row = await create_task(dto.model_copy(update={"created_at": None, "updated_at": None}))
    return to_dto(row)


@router.post("/tasks/generate", response_model=TaskDTO)
async def generate_task_route(req: GenerateTaskRequest, request: Request):
    state = request.app.state
    cp = state.checkpointer
    tup = await cp.aget_tuple({"configurable": {"thread_id": req.session_id}})
    if tup is None:
        raise HTTPException(404, f"session {req.session_id} has no checkpoint")
    messages = tup.checkpoint.get("channel_values", {}).get("messages", []) or []

    llm = resolve_llm(state, req.model)
    try:
        return await generate_task_from_run(session_id=req.session_id, messages=messages, llm=llm)
    except ValueError as e:
        logger.exception("task generator failed")
        raise HTTPException(422, f"task generation failed: {e}") from e
