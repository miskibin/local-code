from langchain_core.runnables import RunnableConfig
from langchain_core.tools import ToolException, tool

from app.artifact_store import build_and_persist_tool_artifact, run_python_artifact


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
    App theme (transparent bg, Geist Mono, blue-led color cycle) is preset on
    `matplotlib.rcParams`; override in your code if you need custom styling.
    Subprocess, 20-second timeout, no state between calls. The summary you see
    starts with the artifact id (looks like `art_abc123def456`).

    Sandbox — DO NOT attempt these (they will be blocked):
    - NO database access: do NOT `import sqlite3 / sqlalchemy / aiosqlite /
      asyncpg / pymongo / redis` (rejected at submit time). For any SQL
      question delegate to the `sql-agent` subagent (or call `sql_query`).
    - NO network: do NOT `import socket / urllib / requests / httpx /
      aiohttp` (rejected at submit time). Don't try to download data.
    - NO subprocess / shell: do NOT `import subprocess`, do NOT call
      `os.system` / `os.popen` / `os.exec*` (rejected at submit time).
    - NO project filesystem: any `open(...)` against project files, `*.db`,
      or `.env*` is blocked at runtime by the in-process audit hook (so it
      raises mid-execution). To read prior data use `read_artifact("art_…")`.
    - NO `__import__`, `eval`, `exec`, `compile`, `ctypes` (rejected at
      submit time).
    Compute, transform DataFrames, and plot with matplotlib — that's it.
    """
    try:
        result = await run_python_artifact(code)
    except (RuntimeError, TimeoutError, ValueError) as e:
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
