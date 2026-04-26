"""Read-only schema tools for the sql-agent sub-agent.

Auto-discovered alongside the regular tools and attached to the sub-agent by
name in `default_subagents()`. The terminal query tool is `sql_query`
(`backend/app/tools/sql_query.py`) — keeping a single tool path so the parent
agent and the sub-agent emit identical SQL artifacts.

Tools are constructed lazily via module `__getattr__` so importing this module
during `discover_tools()` (called per `/chat` turn) does not open a sync
SQLite connection inside an async route handler.
"""

from functools import cache

from langchain_community.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
)
from langchain_community.utilities import SQLDatabase

from app.config import get_settings


@cache
def _db() -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{get_settings().chinook_db_path}")


@cache
def _list_tables_tool() -> ListSQLDatabaseTool:
    return ListSQLDatabaseTool(db=_db())


@cache
def _schema_tool() -> InfoSQLDatabaseTool:
    return InfoSQLDatabaseTool(db=_db())


_LAZY_ATTRS = {
    "sql_db_list_tables": _list_tables_tool,
    "sql_db_schema": _schema_tool,
}


def __getattr__(name: str):
    builder = _LAZY_ATTRS.get(name)
    if builder is None:
        raise AttributeError(name)
    return builder()


def __dir__() -> list[str]:
    return list(_LAZY_ATTRS.keys())
