"""Schema metadata for the sql-agent sub-agent.

The sub-agent's `system_prompt` bakes in the bundled Chinook schema rather
than calling discovery tools at runtime — keeping a single tool path
(`sql_query`) so the parent agent and the sub-agent emit identical SQL
artifacts.

`schema_blob()` is module-cached. Warm it during app startup
(`backend/app/main.py` lifespan) so the first `/chat` doesn't pay sync
SQLite I/O on the event loop.
"""

from functools import cache

from langchain_community.utilities import SQLDatabase

from app.config import get_settings


@cache
def _db() -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{get_settings().chinook_db_path}")


@cache
def schema_blob() -> str:
    return _db().get_table_info()
