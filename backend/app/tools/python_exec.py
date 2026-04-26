import tempfile

from langchain_core.tools import tool
from langchain_sandbox import PyodideSandbox


@tool
async def python_exec(code: str) -> str:
    """Execute Python in a sandboxed Pyodide subprocess. Returns stdout + last expression."""
    try:
        with tempfile.TemporaryDirectory(prefix="pyodide-sess-") as sessions_dir:
            sandbox = PyodideSandbox(sessions_dir, allow_net=False)
            result = await sandbox.execute(code)
            parts: list[str] = []
            if result.stdout:
                parts.append(result.stdout.strip())
            if result.result is not None:
                parts.append(str(result.result))
            if result.stderr:
                parts.append(f"stderr: {result.stderr.strip()}")
            return "\n".join(parts) or "<no output>"
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
