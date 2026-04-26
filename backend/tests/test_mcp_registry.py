from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_sync_from_db_loads_enabled_servers_and_isolates_failures():
    from app.mcp_registry import MCPRegistry
    from app.models import MCPServerConfig

    cfgs = [
        MCPServerConfig(name="good", enabled=True, connection={"command": "echo", "args": [], "transport": "stdio"}),
        MCPServerConfig(name="broken", enabled=True, connection={"command": "doesnotexist", "args": [], "transport": "stdio"}),
        MCPServerConfig(name="off", enabled=False, connection={"command": "echo", "args": [], "transport": "stdio"}),
    ]
    reg = MCPRegistry()

    async def fake_load(name):
        if name == "broken":
            raise RuntimeError("boom")
        return [_FakeTool(f"{name}_t1")]

    with patch.object(reg, "_load_one", new=AsyncMock(side_effect=fake_load)):
        await reg.sync_from_db(cfgs)

    names = [t.name for t in reg.tools]
    assert "good_t1" in names
    assert "off_t1" not in names
    assert all(not n.startswith("broken") for n in names)


class _FakeTool:
    def __init__(self, name):
        self.name = name
