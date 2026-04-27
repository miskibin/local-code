import pytest
from sqlmodel import select


@pytest.mark.asyncio
async def test_create_all_then_persist_session():
    from app.db import async_session, init_db
    from app.models import ChatSession

    await init_db()
    async with async_session() as s:
        s.add(ChatSession(id="abc", title="hello"))
        await s.commit()

    async with async_session() as s:
        result = await s.execute(select(ChatSession).where(ChatSession.id == "abc"))
        row = result.scalar_one()
        assert row.title == "hello"


@pytest.mark.asyncio
async def test_mcp_config_json_blob_roundtrip():
    from app.db import async_session, init_db
    from app.models import MCPServerConfig

    await init_db()
    cfg = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "transport": "stdio",
    }
    async with async_session() as s:
        s.add(MCPServerConfig(name="memory", enabled=True, connection=cfg))
        await s.commit()

    async with async_session() as s:
        from sqlmodel import select

        row = (await s.execute(select(MCPServerConfig))).scalar_one()
        assert row.connection == cfg


@pytest.mark.asyncio
async def test_tool_flag_default_true():
    from app.db import async_session, init_db
    from app.models import ToolFlag

    await init_db()
    async with async_session() as s:
        s.add(ToolFlag(name="python_exec"))
        await s.commit()

    async with async_session() as s:
        from sqlmodel import select

        row = (await s.execute(select(ToolFlag))).scalar_one()
        assert row.enabled is True
