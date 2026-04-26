from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.artifact_store import build_and_persist_tool_artifact, run_python_artifact


@tool(response_format="content_and_artifact")
async def python_exec(code: str, config: RunnableConfig) -> tuple[str, dict]:
    """Run Python and return (summary, artifact). Use for arithmetic, data work, plots.

    Two helpers are injected into your script:

    - `out(obj)` — surface a value as the artifact. List-of-dict → table.
      Else → text. Without `out()` you get a text artifact from stdout.
    - `out_image(fig=None, *, title=None, caption=None)` — emit a matplotlib
      figure as a PNG image artifact. With no arg, captures `plt.gcf()`.
      Example: `import matplotlib.pyplot as plt; plt.bar(x, y); out_image(title='Sales')`.

    matplotlib is available; the Agg backend is set automatically. Subprocess,
    20-second timeout, no state between calls. The summary you see starts with
    the artifact id (looks like `art_abc123def456`).
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
