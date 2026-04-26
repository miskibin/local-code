from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app import tool_registry
from app.db import async_session
from app.models import ToolFlag

router = APIRouter()


class ToolDTO(BaseModel):
    name: str
    enabled: bool
    description: str = ""


class ToolPatch(BaseModel):
    enabled: bool


@router.get("/tools", response_model=list[ToolDTO])
async def list_tools():
    discovered = tool_registry.discover_tools()
    async with async_session() as s:
        flags = {f.name: f.enabled for f in (await s.execute(select(ToolFlag))).scalars().all()}
    return [
        ToolDTO(
            name=t.name,
            enabled=flags.get(t.name, True),
            description=(t.description or "").strip().splitlines()[0] if t.description else "",
        )
        for t in discovered
    ]


@router.patch("/tools/{name}", response_model=ToolDTO)
async def patch_tool(name: str, patch: ToolPatch):
    discovered = {t.name: t for t in tool_registry.discover_tools()}
    if name not in discovered:
        raise HTTPException(404, "unknown tool")
    async with async_session() as s:
        existing = await s.get(ToolFlag, name)
        if existing is None:
            existing = ToolFlag(name=name, enabled=patch.enabled)
            s.add(existing)
        else:
            existing.enabled = patch.enabled
        await s.commit()
    t = discovered[name]
    return ToolDTO(
        name=name,
        enabled=patch.enabled,
        description=(t.description or "").strip().splitlines()[0] if t.description else "",
    )
