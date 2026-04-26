from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.artifact_store import persist_tool_artifact, run_python_artifact


def _session_id(config: RunnableConfig | None) -> str | None:
    return ((config or {}).get("configurable") or {}).get("thread_id")


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
    artifact = {
        "kind": result["kind"],
        "title": result["title"],
        "payload": result["payload"],
        "summary": result["summary"],
        "source_kind": "python",
        "source_code": code,
    }
    row = await persist_tool_artifact(artifact=artifact, session_id=_session_id(config))
    summary = f"{row.id} · {result['summary']}"
    return summary, {**artifact, "id": row.id}
