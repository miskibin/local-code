import asyncio
import subprocess
import sys
import textwrap

from loguru import logger
from langchain_core.tools import tool

TIMEOUT_SECONDS = 20


def _run_sync(code: str) -> str:
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", textwrap.dedent(code)],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"python_exec timeout {TIMEOUT_SECONDS}s")
        return f"error: timed out after {TIMEOUT_SECONDS}s"

    logger.debug(
        f"python_exec exit={proc.returncode} stdout={len(proc.stdout or b'')}b stderr={len(proc.stderr or b'')}b"
    )
    parts: list[str] = []
    if proc.stdout:
        parts.append(proc.stdout.decode("utf-8", errors="replace").rstrip())
    if proc.stderr:
        parts.append("stderr: " + proc.stderr.decode("utf-8", errors="replace").rstrip())
    if proc.returncode != 0 and not parts:
        parts.append(f"exit code {proc.returncode}")
    return "\n".join(parts) or "<no output>"


@tool
async def python_exec(code: str) -> str:
    """Execute Python code and return stdout. Use for arithmetic, data work, snippets.

    Runs the provided code in a fresh Python subprocess with a 20-second timeout.
    Returns combined stdout/stderr as a string. No state persists between calls.
    """
    return await asyncio.to_thread(_run_sync, code)
