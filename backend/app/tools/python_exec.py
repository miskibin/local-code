from langchain_core.runnables import RunnableConfig
from langchain_core.tools import ToolException, tool

from app.artifact_store import build_and_persist_tool_artifact, run_python_artifact
from app.runtime import get_sandbox


def _thread_id_from_config(config: RunnableConfig | None) -> str | None:
    return ((config or {}).get("configurable") or {}).get("thread_id")


@tool(response_format="content_and_artifact")
async def python_exec(code: str, config: RunnableConfig) -> tuple[str, dict]:
    """Run Python and return (summary, artifact). Use for arithmetic, data work, plots.

    Write minimal code. No comments, no docstrings, no prints unless needed for output.

    Three helpers are injected into your script:

    - `out(obj)` — surface a value as the artifact. List-of-dict → table.
      Else → text. Without `out()` you get a text artifact from stdout.
      Pandas DataFrames are NOT auto-converted; pass
      `df.reset_index().to_dict("records")` if you want a table artifact.
    - `out_image(fig=None, *, title=None, caption=None)` — emit a matplotlib
      figure as a PNG image artifact. With no arg, captures `plt.gcf()`.
      Example: `import matplotlib.pyplot as plt; plt.bar(x, y); out_image(title='Sales')`.
    - `read_artifact(id)` — load a prior artifact by its bare id (e.g.
      `read_artifact("art_abc123def456")`). Tables come back as a pandas
      DataFrame; images as raw PNG bytes; text as a str. Only ids that
      appear literally in the script source are staged for the run, so write
      the id as a string literal — never read it from a CSV/file path that
      doesn't exist.

    matplotlib and pandas are available; the Agg backend is set automatically.
    App theme (transparent bg, blue-led color cycle) is preset on
    `matplotlib.rcParams`; override in your code if you need custom styling.

    State PERSISTS across calls within one chat thread: variables, imports
    and DataFrames stay alive between runs. Reset the thread to clear.
    Sandboxed in Pyodide (Deno+WASM); no host filesystem access, no env
    vars, no arbitrary network.
    """
    try:
        result = await run_python_artifact(
            code,
            sandbox=get_sandbox(),
            session_id=_thread_id_from_config(config),
        )
    except (RuntimeError, TimeoutError) as e:
        raise ToolException(f"error: {e}") from e
    return await build_and_persist_tool_artifact(
        result=result,
        source_kind="python",
        source_code=code,
        config=config,
    )


# Surface ToolException as a ToolMessage(status="error") so the streaming
# layer routes it to `tool-output-error` and the UI shows a Failed state.
python_exec.handle_tool_error = True
