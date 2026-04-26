from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.artifact_store import persist_tool_artifact, run_sql_artifact


def _session_id(config: RunnableConfig | None) -> str | None:
    return ((config or {}).get("configurable") or {}).get("thread_id")


@tool(response_format="content_and_artifact")
async def sql_query(sql: str, config: RunnableConfig) -> tuple[str, dict]:
    """Run a SQL query against the bundled Chinook SQLite DB and return (summary, table artifact).

    Use this for one-shot reads. Result rows are capped at 200; check the summary
    for `[truncated to 200]` and refine the query if needed. The summary starts
    with the artifact id (looks like `art_abc123def456`) — pass that bare id
    (no brackets, no quotes) to the `chart` tool's `artifact_id` parameter.
    """
    try:
        result = await run_sql_artifact(sql)
    except Exception as e:
        return f"sql error: {e}", {}
    artifact = {
        "kind": result["kind"],
        "title": result["title"],
        "payload": result["payload"],
        "summary": result["summary"],
        "source_kind": "sql",
        "source_code": sql,
    }
    row = await persist_tool_artifact(artifact=artifact, session_id=_session_id(config))
    summary = f"{row.id} · {result['summary']}"
    return summary, {**artifact, "id": row.id}
