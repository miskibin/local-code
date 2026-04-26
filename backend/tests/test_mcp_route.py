from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_post_mcp_persists_and_triggers_sync():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.mcp_registry import MCPRegistry
    from app.models import MCPServerConfig

    app = create_app()
    await init_db()

    # Clean any prior rows (in-memory sqlite is shared across tests)
    async with async_session() as s:
        await s.execute(delete(MCPServerConfig))
        await s.commit()

    app.state.mcp_registry = MCPRegistry()
    app.state.mcp_registry.sync_from_db = AsyncMock()

    payload = {
        "name": "memory",
        "enabled": True,
        "connection": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"], "env": {}, "transport": "stdio"},
    }
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/mcp", json=payload)
            assert r.status_code == 200

            r2 = await ac.get("/mcp")
            assert any(c["name"] == "memory" for c in r2.json())

            r3 = await ac.delete("/mcp/memory")
            assert r3.status_code == 200

        assert app.state.mcp_registry.sync_from_db.call_count >= 2
    finally:
        async with async_session() as s:
            await s.execute(delete(MCPServerConfig))
            await s.commit()
