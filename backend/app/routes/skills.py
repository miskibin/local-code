from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.auth import CurrentUser
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


class SkillContentDTO(BaseModel):
    markdown: str


@router.get("/skills", response_model=list[SkillDTO])
async def list_skills(user: CurrentUser):
    discovered = discover_skills(get_settings().skills_dir)
    async with async_session() as s:
        rows = (
            (await s.execute(select(SkillFlag).where(SkillFlag.user_id == user.id))).scalars().all()
        )
        flags = {f.name: f.enabled for f in rows}
    return [
        SkillDTO(name=sk.name, description=sk.description, enabled=flags.get(sk.name, True))
        for sk in discovered
    ]


@router.patch("/skills/{name}", response_model=SkillDTO)
async def patch_skill(name: str, patch: SkillPatch, user: CurrentUser):
    discovered = {sk.name: sk for sk in discover_skills(get_settings().skills_dir)}
    if name not in discovered:
        raise HTTPException(404, "unknown skill")
    async with async_session() as s:
        existing = await s.get(SkillFlag, (user.id, name))
        if existing is None:
            existing = SkillFlag(user_id=user.id, name=name, enabled=patch.enabled)
            s.add(existing)
        else:
            existing.enabled = patch.enabled
        await s.commit()
    sk = discovered[name]
    return SkillDTO(name=name, description=sk.description, enabled=patch.enabled)


@router.get("/skills/{name}/content", response_model=SkillContentDTO)
async def get_skill_content(name: str, user: CurrentUser):
    discovered = {sk.name: sk for sk in discover_skills(get_settings().skills_dir)}
    if name not in discovered:
        raise HTTPException(404, "unknown skill")
    return SkillContentDTO(markdown=discovered[name].body)
