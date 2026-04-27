from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.config import get_settings
from app.db import async_session
from app.models import SkillFlag
from app.skills_registry import discover_skills

router = APIRouter()


class SkillDTO(BaseModel):
    name: str
    enabled: bool
    description: str


class SkillPatch(BaseModel):
    enabled: bool


@router.get("/skills", response_model=list[SkillDTO])
async def list_skills():
    discovered = discover_skills(get_settings().skills_dir)
    async with async_session() as s:
        flags = {f.name: f.enabled for f in (await s.execute(select(SkillFlag))).scalars().all()}
    return [
        SkillDTO(name=sk.name, description=sk.description, enabled=flags.get(sk.name, True))
        for sk in discovered
    ]


@router.patch("/skills/{name}", response_model=SkillDTO)
async def patch_skill(name: str, patch: SkillPatch):
    discovered = {sk.name: sk for sk in discover_skills(get_settings().skills_dir)}
    if name not in discovered:
        raise HTTPException(404, "unknown skill")
    async with async_session() as s:
        existing = await s.get(SkillFlag, name)
        if existing is None:
            existing = SkillFlag(name=name, enabled=patch.enabled)
            s.add(existing)
        else:
            existing.enabled = patch.enabled
        await s.commit()
    sk = discovered[name]
    return SkillDTO(name=name, description=sk.description, enabled=patch.enabled)
