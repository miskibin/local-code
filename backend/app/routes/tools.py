from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sqlmodel import select

from app import tool_registry
from app.auth import CurrentUser
from app.db import async_session
from app.models import ToolFlag

router = APIRouter()


class ToolDTO(BaseModel):
    name: str
    enabled: bool
    description: str = ""
    source: Literal["builtin", "mcp"] = "builtin"
    server: str | None = None
    args_schema: dict[str, Any] | None = None


class ToolPatch(BaseModel):
    enabled: bool


def _extract_args_schema(tool: BaseTool) -> dict[str, Any] | None:
    schema = getattr(tool, "args_schema", None)
    if schema is None:
        return None
    if isinstance(schema, dict):
        return schema
    fn = getattr(schema, "model_json_schema", None)
    if callable(fn):
        return fn()
    return None


def _short_description(tool: BaseTool) -> str:
    if not tool.description:
        return ""
    return tool.description.strip().splitlines()[0]


@router.get("/tools", response_model=list[ToolDTO])
async def list_tools(request: Request, user: CurrentUser):
    builtin = tool_registry.discover_tools()
    mcp_registry = getattr(request.app.state, "mcp_registry", None)
    mcp_tools: list[BaseTool] = mcp_registry.tools if mcp_registry is not None else []
    tools_by_server: dict[str, list[str]] = (
        mcp_registry.tools_by_server if mcp_registry is not None else {}
    )
    name_to_server = {
        tool_name: server for server, names in tools_by_server.items() for tool_name in names
    }

    async with async_session() as s:
        rows = (
            (await s.execute(select(ToolFlag).where(ToolFlag.user_id == user.id))).scalars().all()
        )
    flags = {f.name: f.enabled for f in rows}

    out: list[ToolDTO] = []
    for t in builtin:
        out.append(
            ToolDTO(
                name=t.name,
                enabled=flags.get(t.name, True),
                description=_short_description(t),
                source="builtin",
                server=None,
                args_schema=_extract_args_schema(t),
            )
        )
    for t in mcp_tools:
        out.append(
            ToolDTO(
                name=t.name,
                enabled=flags.get(t.name, True),
                description=_short_description(t),
                source="mcp",
                server=name_to_server.get(t.name),
                args_schema=_extract_args_schema(t),
            )
        )
    return out


@router.patch("/tools/{name}", response_model=ToolDTO)
async def patch_tool(name: str, patch: ToolPatch, request: Request, user: CurrentUser):
    builtin = {t.name: t for t in tool_registry.discover_tools()}
    mcp_registry = getattr(request.app.state, "mcp_registry", None)
    mcp_map: dict[str, BaseTool] = (
        {t.name: t for t in mcp_registry.tools} if mcp_registry is not None else {}
    )
    tools_by_server: dict[str, list[str]] = (
        mcp_registry.tools_by_server if mcp_registry is not None else {}
    )
    if name in builtin:
        tool = builtin[name]
        source: Literal["builtin", "mcp"] = "builtin"
        server: str | None = None
    elif name in mcp_map:
        tool = mcp_map[name]
        source = "mcp"
        server = next(
            (srv for srv, names in tools_by_server.items() if name in names),
            None,
        )
    else:
        raise HTTPException(404, "unknown tool")

    async with async_session() as s:
        existing = await s.get(ToolFlag, (user.id, name))
        if existing is None:
            existing = ToolFlag(user_id=user.id, name=name, enabled=patch.enabled)
            s.add(existing)
        else:
            existing.enabled = patch.enabled
        await s.commit()
    return ToolDTO(
        name=name,
        enabled=patch.enabled,
        description=_short_description(tool),
        source=source,
        server=server,
        args_schema=_extract_args_schema(tool),
    )
