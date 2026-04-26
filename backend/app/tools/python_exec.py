import asyncio
import sys
import textwrap

from langchain_core.tools import tool

TIMEOUT_SECONDS = 20


@tool
async def python_exec(code: str) -> str:
    """Execute Python code and return stdout. Use for arithmetic, data work, snippets.

    Runs the provided code in a fresh Python subprocess with a 20-second timeout.
    Returns combined stdout/stderr as a string. No state persists between calls.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-c",
        textwrap.dedent(code),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"error: timed out after {TIMEOUT_SECONDS}s"

    parts: list[str] = []
    if out:
        parts.append(out.decode("utf-8", errors="replace").rstrip())
    if err:
        parts.append("stderr: " + err.decode("utf-8", errors="replace").rstrip())
    if proc.returncode != 0 and not parts:
        parts.append(f"exit code {proc.returncode}")
    return "\n".join(parts) or "<no output>"
