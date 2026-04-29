import importlib
import inspect
import pkgutil

from loguru import logger

from app import commands as commands_pkg
from app.commands.base import Command


def discover_commands() -> dict[str, Command]:
    found: dict[str, Command] = {}
    for _, modname, _ in pkgutil.iter_modules(commands_pkg.__path__, commands_pkg.__name__ + "."):
        if modname.endswith((".base", ".dispatcher", ".registry")):
            continue
        mod = importlib.import_module(modname)
        for _, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) or not isinstance(obj, Command):
                continue
            if obj.name in found:
                continue
            found[obj.name] = obj
    logger.info(f"discovered {len(found)} slash commands: {sorted(found)}")
    return found
