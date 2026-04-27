from typing import Any

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import select

from app.db import async_session
from app.models import MCPServerConfig

router = APIRouter()


class MCPDTO(BaseModel):
    name: str
    enabled: bool
    connection: dict[str, Any]
    resolved_tools: list[str] = Field(default_factory=list)


async def _load_all() -> list[MCPServerConfig]:
    async with async_session() as s:
        return list((await s.execute(select(MCPServerConfig))).scalars().all())


async def _resync(request: Request) -> None:
    cfgs = await _load_all()
    await request.app.state.mcp_registry.sync_from_db(cfgs)


@router.get("/mcp", response_model=list[MCPDTO])
async def list_mcp(request: Request):
    rows = await _load_all()
    by_server = request.app.state.mcp_registry.tools_by_server
    out: list[MCPDTO] = []
    for row in rows:
        resolved = (
            [] if not row.enabled else list(by_server.get(row.name, []))
        )
        out.append(
            MCPDTO(
                name=row.name,
                enabled=row.enabled,
                connection=row.connection,
                resolved_tools=resolved,
            )
        )
    return out


@router.post("/mcp", response_model=MCPDTO)
async def upsert_mcp(dto: MCPDTO, request: Request):
    async with async_session() as s:
        existing = await s.get(MCPServerConfig, dto.name)
        if existing is None:
            s.add(MCPServerConfig(**dto.model_dump(exclude={"resolved_tools"})))
        else:
            existing.enabled = dto.enabled
            existing.connection = dto.connection
        await s.commit()
    logger.info(f"mcp upsert {dto.name!r} enabled={dto.enabled} -> resync")
    await _resync(request)
    by_server = request.app.state.mcp_registry.tools_by_server
    resolved = [] if not dto.enabled else list(by_server.get(dto.name, []))
    return MCPDTO(
        name=dto.name,
        enabled=dto.enabled,
        connection=dto.connection,
        resolved_tools=resolved,
    )


@router.delete("/mcp/{name}")
async def delete_mcp(name: str, request: Request):
    async with async_session() as s:
        existing = await s.get(MCPServerConfig, name)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    logger.info(f"mcp delete {name!r} -> resync")
    await _resync(request)
    return {"deleted": name}
