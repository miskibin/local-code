import asyncio

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from loguru import logger


class MCPRegistry:
    def __init__(self) -> None:
        self._tools: list[BaseTool] = []
        self._tools_by_server: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()
        # Context managers for open sessions; kept alive so tools can call back
        # into the MCP server after startup. Closed on next sync_from_db.
        self._session_cms: list = []

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._tools)

    @property
    def tools_by_server(self) -> dict[str, list[str]]:
        return dict(self._tools_by_server)

    async def sync_from_db(self, configs: list) -> None:
        async with self._lock:
            for cm in self._session_cms:
                try:  # noqa: SIM105
                    await cm.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001
                    pass
            self._session_cms = []
            self._tools_by_server = {}

            enabled = {c.name: c.connection for c in configs if c.enabled}
            logger.info(f"mcp sync: {len(enabled)} enabled servers")

            client = MultiServerMCPClient(connections=enabled)
            new_tools: list[BaseTool] = []
            for name in list(enabled):
                try:
                    cm = client.session(name)
                    session = await cm.__aenter__()
                    self._session_cms.append(cm)
                    tools = await load_mcp_tools(session)
                    self._tools_by_server[name] = [t.name for t in tools]
                    new_tools.extend(tools)
                    logger.debug(f"mcp server {name!r}: loaded {len(tools)} tools")
                except Exception as e:  # noqa: BLE001 -- skip unreachable server
                    logger.warning(f"MCP server {name!r} unavailable: {e}")
                    self._tools_by_server[name] = []

            self._tools = new_tools
            logger.info(f"mcp sync done: {len(new_tools)} tools across {len(enabled)} servers")
