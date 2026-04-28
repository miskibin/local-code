from typing import Any

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import select

from app.auth import CurrentAdmin, CurrentUser
from app.db import async_session
from app.models import MCPServerConfig, MCPServerUserFlag

router = APIRouter()


class MCPDTO(BaseModel):
    name: str
    enabled: bool
    connection: dict[str, Any]
    resolved_tools: list[str] = Field(default_factory=list)


class MCPUserFlagPatch(BaseModel):
    enabled: bool


async def _load_all() -> list[MCPServerConfig]:
    async with async_session() as s:
        return list((await s.execute(select(MCPServerConfig))).scalars().all())


async def _load_user_flags(user_id: str) -> dict[str, bool]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(MCPServerUserFlag).where(MCPServerUserFlag.user_id == user_id)))
            .scalars()
            .all()
        )
    return {r.name: r.enabled for r in rows}


async def _resync(request: Request) -> None:
    cfgs = await _load_all()
    await request.app.state.mcp_registry.sync_from_db(cfgs)


def _build_mcp_dto(
    *, name: str, enabled: bool, connection: dict[str, Any], by_server: dict[str, list[str]]
) -> MCPDTO:
    resolved = [] if not enabled else list(by_server.get(name, []))
    return MCPDTO(
        name=name,
        enabled=enabled,
        connection=connection,
        resolved_tools=resolved,
    )


@router.get("/mcp", response_model=list[MCPDTO])
async def list_mcp(request: Request, user: CurrentUser):
    rows = await _load_all()
    user_flags = await _load_user_flags(user.id)
    by_server = request.app.state.mcp_registry.tools_by_server
    return [
        _build_mcp_dto(
            name=row.name,
            # the row appears enabled to the user iff both global + per-user are on
            enabled=row.enabled and user_flags.get(row.name, True),
            connection=row.connection,
            by_server=by_server,
        )
        for row in rows
    ]


@router.post("/mcp", response_model=MCPDTO)
async def upsert_mcp(dto: MCPDTO, request: Request, _admin: CurrentAdmin):
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
    return _build_mcp_dto(
        name=dto.name,
        enabled=dto.enabled,
        connection=dto.connection,
        by_server=request.app.state.mcp_registry.tools_by_server,
    )


@router.patch("/mcp/{name}/me", response_model=MCPDTO)
async def patch_mcp_user_flag(
    name: str,
    patch: MCPUserFlagPatch,
    request: Request,
    user: CurrentUser,
):
    async with async_session() as s:
        cfg = await s.get(MCPServerConfig, name)
        if cfg is None:
            raise HTTPException(404, "unknown mcp server")
        existing = await s.get(MCPServerUserFlag, (user.id, name))
        if existing is None:
            s.add(MCPServerUserFlag(user_id=user.id, name=name, enabled=patch.enabled))
        else:
            existing.enabled = patch.enabled
        await s.commit()
    by_server = request.app.state.mcp_registry.tools_by_server
    return _build_mcp_dto(
        name=name,
        enabled=cfg.enabled and patch.enabled,
        connection=cfg.connection,
        by_server=by_server,
    )


@router.delete("/mcp/{name}")
async def delete_mcp(name: str, request: Request, _admin: CurrentAdmin):
    async with async_session() as s:
        existing = await s.get(MCPServerConfig, name)
        if existing is None:
            raise HTTPException(404)
        await s.delete(existing)
        await s.commit()
    logger.info(f"mcp delete {name!r} -> resync")
    await _resync(request)
    return {"deleted": name}
