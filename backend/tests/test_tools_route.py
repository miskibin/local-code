import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_tools_list_reflects_discovered_and_flags(monkeypatch):
    from app.db import init_db
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    await init_db()

    # Stub discovery to a known set
    from langchain_core.tools import tool

    from app import tool_registry

    @tool
    def stub_tool() -> str:
        """stub"""
        return "ok"

    monkeypatch.setattr(tool_registry, "discover_tools", lambda: [stub_tool])

    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.get("/tools")
    assert r.status_code == 200
    body = r.json()
    assert any(t["name"] == "stub_tool" for t in body)
    assert all(t["enabled"] is True for t in body)


@pytest.mark.asyncio
async def test_patch_tool_updates_flag(monkeypatch):
    from langchain_core.tools import tool

    from app import tool_registry
    from app.db import init_db
    from app.main import create_app

    @tool
    def stub_tool() -> str:
        """stub"""
        return "ok"

    monkeypatch.setattr(tool_registry, "discover_tools", lambda: [stub_tool])

    app = create_app()
    transport = ASGITransport(app=app)
    await init_db()

    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.patch("/tools/stub_tool", json={"enabled": False})
        assert r.status_code == 200
        r2 = await ac.get("/tools")
        assert any(t["name"] == "stub_tool" and t["enabled"] is False for t in r2.json())
