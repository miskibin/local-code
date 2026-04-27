from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_session_cm(*, fail: bool = False):
    cm = MagicMock()
    if fail:
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))
    else:
        cm.__aenter__ = AsyncMock(return_value=MagicMock())
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.asyncio
async def test_sync_from_db_loads_enabled_servers_and_isolates_failures():
    from app.mcp_registry import MCPRegistry
    from app.models import MCPServerConfig

    cfgs = [
        MCPServerConfig(name="good", enabled=True, connection={"transport": "stdio"}),
        MCPServerConfig(name="broken", enabled=True, connection={"transport": "stdio"}),
        MCPServerConfig(name="off", enabled=False, connection={"transport": "stdio"}),
    ]
    reg = MCPRegistry()

    with (
        patch("app.mcp_registry.MultiServerMCPClient") as mock_cls,
        patch("app.mcp_registry.load_mcp_tools", new=AsyncMock(return_value=[_FakeTool("good_t1")])),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.session = lambda name: _make_session_cm(fail=(name == "broken"))

        await reg.sync_from_db(cfgs)

    names = [t.name for t in reg.tools]
    assert "good_t1" in names
    assert "off_t1" not in names
    assert all(not n.startswith("broken") for n in names)


class _FakeTool:
    def __init__(self, name):
        self.name = name
