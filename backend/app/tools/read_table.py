from langchain_core.tools import ToolException, tool

from app.artifact_store import get_artifact
from app.services.table_summary import build_table_summary


@tool
async def read_table_summary(artifact_id: str) -> str:
    """Return a low-context summary of a table artifact (schema + small head).

    Use this whenever you need to understand the shape of a table — uploaded
    CSV, SQL result, or python_exec result — before deciding which columns to
    pull or which transform to apply. Pass the bare id (e.g. `art_abc123`).
    Cheap by design: schema + first ~5 rows; for actual data crunching use
    `python_exec` with `read_artifact(id)`.
    """
    artifact = await get_artifact(artifact_id)
    if artifact is None:
        raise ToolException(f"artifact {artifact_id} not found")
    if artifact.kind != "table":
        raise ToolException(f"artifact {artifact_id} is kind={artifact.kind}, not table")
    return build_table_summary(artifact)


# Surface ToolException as ToolMessage(status="error") so a wrong-kind id
# doesn't tear down the stream — UI shows a Failed state and the agent can recover.
read_table_summary.handle_tool_error = True
