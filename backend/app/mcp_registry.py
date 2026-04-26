import asyncio
from loguru import logger
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


class MCPRegistry:
    def __init__(self) -> None:
        self.client = MultiServerMCPClient(connections={})
        self._tools: list[BaseTool] = []
        self._lock = asyncio.Lock()

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._tools)

    async def sync_from_db(self, configs: list) -> None:
        async with self._lock:
            self.client.connections = {
                c.name: c.connection for c in configs if c.enabled
            }
            new_tools: list[BaseTool] = []
            for name in list(self.client.connections):
                try:
                    new_tools.extend(await self._load_one(name))
                except Exception as e:
                    logger.warning(f"MCP server {name!r} unavailable: {e}")
            self._tools = new_tools

    async def _load_one(self, name: str) -> list[BaseTool]:
        async with self.client.session(name) as session:
            return await load_mcp_tools(session)
