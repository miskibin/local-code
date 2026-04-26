import importlib
import inspect
import pkgutil

from langchain_core.tools import BaseTool
from loguru import logger

from app import tools as tools_pkg


def discover_tools() -> list[BaseTool]:
    found: list[BaseTool] = []
    for _, name, _ in pkgutil.iter_modules(tools_pkg.__path__, tools_pkg.__name__ + "."):
        mod = importlib.import_module(name)
        for _, obj in inspect.getmembers(mod):
            if isinstance(obj, BaseTool):
                found.append(obj)
    logger.debug(f"discovered {len(found)} local tools: {[t.name for t in found]}")
    return found


def active_tools(
    local: list[BaseTool],
    mcp: list[BaseTool],
    flags: dict[str, bool],
) -> list[BaseTool]:
    result = [t for t in (local + mcp) if flags.get(t.name, True)]
    logger.debug(
        f"active_tools: {len(result)}/{len(local) + len(mcp)} after flag filter"
    )
    return result
