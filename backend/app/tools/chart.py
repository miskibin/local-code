import json
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.artifact_store import build_and_persist_tool_artifact, run_chart_artifact


@tool(response_format="content_and_artifact")
async def chart(
    artifact_id: str,
    x: str,
    y: str,
    config: RunnableConfig,
    kind: Literal["bar", "line"] = "bar",
    title: str = "Chart",
) -> tuple[str, dict]:
    """Build a chart from a prior table artifact (referenced by id).

    Returns (summary, chart artifact).

    `artifact_id` MUST be the bare id string from a previous tool's summary
    (the token at the very start, before the ` · ` separator — looks like
    `art_abc123def456`). Do NOT pass placeholders like `[artifact_id=...]`,
    quotes, or the literal string "artifact_id".

    Reads the table artifact, picks columns `x` (labels) and `y` (numeric
    values), and emits a chart artifact. The raw rows are never sent back
    to the model — only a summary plus the chart payload.
    """
    spec = {"artifact_id": artifact_id, "x": x, "y": y, "kind": kind, "title": title}
    try:
        result = await run_chart_artifact(spec)
    except (LookupError, ValueError) as e:
        return f"chart error: {e}", {}
    return await build_and_persist_tool_artifact(
        result=result,
        source_kind="chart",
        source_code=json.dumps(spec, separators=(",", ":")),
        config=config,
        parent_artifact_ids=[artifact_id],
    )
