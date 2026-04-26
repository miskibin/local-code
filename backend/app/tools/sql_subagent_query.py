"""Read-only schema tools for the sql-agent sub-agent.

Auto-discovered alongside the regular tools and attached to the sub-agent by
name in `default_subagents()`. The terminal query tool is `sql_query`
(`backend/app/tools/sql_query.py`) — keeping a single tool path so the parent
agent and the sub-agent emit identical SQL artifacts.
"""

from langchain_community.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
)
from langchain_community.utilities import SQLDatabase

from app.config import get_settings


def _db() -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{get_settings().chinook_db_path}")


sql_db_list_tables = ListSQLDatabaseTool(db=_db())
sql_db_schema = InfoSQLDatabaseTool(db=_db())
