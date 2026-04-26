from langchain_core.runnables import RunnableConfig
from langchain_core.tools import ToolException, tool
from sqlalchemy.exc import SQLAlchemyError

from app.artifact_store import build_and_persist_tool_artifact, run_sql_artifact


@tool(response_format="content_and_artifact")
async def sql_query(sql: str, config: RunnableConfig) -> tuple[str, dict]:
    """Run a SQL query against the bundled Chinook SQLite DB and return (summary, table artifact).

    Use this for one-shot reads. Result rows are capped at 200; check the summary
    for `[truncated to 200]` and refine the query if needed. The summary starts
    with the artifact id (looks like `art_abc123def456`). To plot the result,
    call `python_exec` with matplotlib; load the rows via `read_artifact(id)`.
    """
    try:
        result = await run_sql_artifact(sql)
    except (FileNotFoundError, SQLAlchemyError) as e:
        raise ToolException(f"sql error: {e}") from e
    return await build_and_persist_tool_artifact(
        result=result,
        source_kind="sql",
        source_code=sql,
        config=config,
    )


# See python_exec for the rationale — surface ToolException as ToolMessage(error).
sql_query.handle_tool_error = True
