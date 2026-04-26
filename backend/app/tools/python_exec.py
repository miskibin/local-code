from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.artifact_store import build_and_persist_tool_artifact, run_python_artifact


@tool(response_format="content_and_artifact")
async def python_exec(code: str, config: RunnableConfig) -> tuple[str, dict]:
    """Run Python and return (summary, artifact). Use for arithmetic, data work, snippets.

    The runner injects a helper `out(obj)` — call it once with the value you want
    to surface as the artifact. List-of-dict → table. {labels, values} dict → chart.
    Else → text. Without `out()` you get a text artifact from stdout.

    Subprocess, 20-second timeout, no state between calls. The summary you see
    starts with the artifact id (looks like `art_abc123def456`) — pass that bare
    id (no brackets, no quotes) to the `chart` tool's `artifact_id` parameter
    to plot the result without re-fetching the rows.
    """
    try:
        result = await run_python_artifact(code)
    except (RuntimeError, TimeoutError) as e:
        return f"error: {e}", {}
    return await build_and_persist_tool_artifact(
        result=result,
        source_kind="python",
        source_code=code,
        config=config,
    )
