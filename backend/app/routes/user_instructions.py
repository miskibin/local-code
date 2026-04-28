from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser
from app.db import async_session
from app.models import UserInstructions
from app.utils import now_utc

router = APIRouter()

MAX_LEN = 50_000


class InstructionsDTO(BaseModel):
    content: str
    updated_at: datetime


class InstructionsPut(BaseModel):
    content: str = Field(default="", max_length=MAX_LEN)


@router.get("/user/instructions", response_model=InstructionsDTO)
async def get_instructions(user: CurrentUser):
    async with async_session() as s:
        row = await s.get(UserInstructions, user.id)
    if row is None:
        return InstructionsDTO(content="", updated_at=now_utc())
    return InstructionsDTO(content=row.content, updated_at=row.updated_at)


@router.put("/user/instructions", response_model=InstructionsDTO)
async def put_instructions(payload: InstructionsPut, user: CurrentUser):
    if len(payload.content) > MAX_LEN:
        raise HTTPException(422, f"content exceeds {MAX_LEN} characters")
    async with async_session() as s:
        row = await s.get(UserInstructions, user.id)
        if row is None:
            row = UserInstructions(user_id=user.id, content=payload.content, updated_at=now_utc())
            s.add(row)
        else:
            row.content = payload.content
            row.updated_at = now_utc()
        await s.commit()
        await s.refresh(row)
    return InstructionsDTO(content=row.content, updated_at=row.updated_at)
