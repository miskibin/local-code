import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from loguru import logger


class MCPRegistry:
    """Multi-reader / single-writer registry of live MCP tools.

    Reads (`pin_for_stream`) hold the current tool refs for the duration of
    an in-flight `/chat` stream. Writes (`sync_from_db`) close the existing
    MCP sessions and open new ones; doing that while a stream is mid-call
    leaves the stream's tool refs pointing at closed sessions and the
    generator hangs or errors. The condition variable below blocks a sync
    until all active streams have drained, and blocks new streams from
    starting while a sync is in progress.
    """

    def __init__(self) -> None:
        self._tools: list[BaseTool] = []
        self._tools_by_server: dict[str, list[str]] = {}
        # Context managers for open sessions; kept alive so tools can call back
        # into the MCP server after startup. Closed on next sync_from_db.
        self._session_cms: list = []
        self._cond = asyncio.Condition()
        self._readers = 0
        self._writing = False

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._tools)

    @property
    def tools_by_server(self) -> dict[str, list[str]]:
        return dict(self._tools_by_server)

    @asynccontextmanager
    async def pin_for_stream(self) -> AsyncIterator[list[BaseTool]]:
        """Snapshot current tools and block any concurrent `sync_from_db`
        until the stream finishes. Yields the pinned tool list."""
        async with self._cond:
            while self._writing:
                await self._cond.wait()
            self._readers += 1
            pinned = list(self._tools)
        try:
            yield pinned
        finally:
            async with self._cond:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()

    async def sync_from_db(self, configs: list) -> None:
        # Mark writer-pending and wait for in-flight streams to drain so we
        # don't tear down sessions a stream is still using.
        async with self._cond:
            while self._writing:
                await self._cond.wait()
            self._writing = True
            while self._readers > 0:
                await self._cond.wait()
        try:
            for cm in self._session_cms:
                try:
                    await cm.__aexit__(None, None, None)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"mcp session teardown failed: {e}")
            self._session_cms = []
            self._tools_by_server = {}

            enabled = {c.name: c.connection for c in configs if c.enabled}
            logger.info(f"mcp sync: {len(enabled)} enabled servers")

            client = MultiServerMCPClient(connections=enabled)
            new_tools: list[BaseTool] = []
            for name in list(enabled):
                try:
                    cm = client.session(name)
                    session = await asyncio.wait_for(cm.__aenter__(), timeout=10)
                    self._session_cms.append(cm)
                    tools = await asyncio.wait_for(load_mcp_tools(session), timeout=10)
                    self._tools_by_server[name] = [t.name for t in tools]
                    new_tools.extend(tools)
                    logger.debug(f"mcp server {name!r}: loaded {len(tools)} tools")
                except Exception as e:  # noqa: BLE001 -- skip unreachable server
                    logger.warning(f"MCP server {name!r} unavailable: {e}")
                    self._tools_by_server[name] = []

            self._tools = new_tools
            logger.info(f"mcp sync done: {len(new_tools)} tools across {len(enabled)} servers")
        finally:
            async with self._cond:
                self._writing = False
                self._cond.notify_all()
