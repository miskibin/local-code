"""Pyodide sandbox tests for `python_exec` (replaces subprocess executor).

Slow: each call boots Deno + Pyodide (~3-5 s warm, ~30+ s cold first call
per fresh sessions_dir). Skipped if Deno isn't on PATH so CI without it stays
green.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

# Cold first call needs longer than the production default while Pyodide
# downloads + caches packages.
os.environ["PYTHON_SANDBOX_TIMEOUT"] = "180"

from app.artifact_store import run_python_artifact  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("deno"), reason="deno binary required")


@pytest.fixture(scope="module")
def sandbox():
    from langchain_sandbox import PyodideSandbox

    from app.python_sandbox import _deno_cache_dir

    # Sessions dir must live under cwd (or same drive at least) so the relative
    # tempfile path passed via `-f` resolves on Windows.
    tmp = tempfile.mkdtemp(prefix="lc_test_sb_", dir=Path.cwd())
    sb = PyodideSandbox(
        sessions_dir=tmp,
        allow_net=["cdn.jsdelivr.net", "pypi.org", "files.pythonhosted.org"],
        allow_read=[tmp, _deno_cache_dir(), "node_modules", str(Path.cwd())],
        allow_write=[tmp],
    )
    yield sb
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sid():
    return f"test-{uuid.uuid4().hex[:8]}"


async def test_simple_print(sandbox, sid):
    result = await run_python_artifact("print('hi')", sandbox=sandbox, session_id=sid)
    assert result["kind"] == "text"
    assert "hi" in result["payload"]["text"]


async def test_table_artifact(sandbox, sid):
    result = await run_python_artifact(
        "out([{'a': 1, 'b': 2}, {'a': 3, 'b': 4}])",
        sandbox=sandbox,
        session_id=sid,
    )
    assert result["kind"] == "table"
    assert result["payload"]["rows"] == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


async def test_image_artifact(sandbox, sid):
    code = (
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1, 2, 3])\n"
        "out_image(title='t')\n"
    )
    result = await run_python_artifact(code, sandbox=sandbox, session_id=sid)
    assert result["kind"] == "image"
    assert result["payload"]["format"] == "png"
    # PNG header magic in raw bytes; just confirm we have substantial b64
    assert len(result["payload"]["data_b64"]) > 100


async def test_state_persists_within_session(sandbox, sid):
    await run_python_artifact("x = 42", sandbox=sandbox, session_id=sid)
    result = await run_python_artifact("print(x * 2)", sandbox=sandbox, session_id=sid)
    assert "84" in result["payload"]["text"]


async def test_state_isolated_between_sessions(sandbox):
    a = f"sess-a-{uuid.uuid4().hex[:8]}"
    b = f"sess-b-{uuid.uuid4().hex[:8]}"
    await run_python_artifact("secret = 'A'", sandbox=sandbox, session_id=a)
    with pytest.raises(RuntimeError, match="NameError"):
        await run_python_artifact("print(secret)", sandbox=sandbox, session_id=b)


async def test_reset_clears_state(sandbox, sid):
    from app.python_sandbox import reset_session

    # config used by reset_session points at sandbox's sessions_dir; piggy-back
    # by monkeypatching settings via the same dir.
    from app.config import get_settings

    settings = get_settings()
    original = settings.python_sessions_dir
    settings.python_sessions_dir = sandbox.sessions_dir
    try:
        await run_python_artifact("y = 99", sandbox=sandbox, session_id=sid)
        reset_session(sid)
        with pytest.raises(RuntimeError, match="NameError"):
            await run_python_artifact("print(y)", sandbox=sandbox, session_id=sid)
    finally:
        settings.python_sessions_dir = original


async def test_host_filesystem_blocked(sandbox, sid):
    # Pyodide-Python is jailed in MEMFS; opening host paths fails inside Python.
    code = "open(r'C:/Windows/System32/drivers/etc/hosts').read()"
    with pytest.raises(RuntimeError):
        await run_python_artifact(code, sandbox=sandbox, session_id=sid)


async def test_js_deno_filesystem_escape_blocked(sandbox, sid):
    # Without narrow allow_read, agent could escape via js.Deno.readTextFile.
    # Confirm the narrowed read list raises NotCapable for arbitrary paths.
    code = (
        "import js\n"
        "async def go():\n"
        "    try:\n"
        "        await js.Deno.readTextFile(r'C:/Windows/System32/drivers/etc/hosts')\n"
        "        return 'LEAKED'\n"
        "    except Exception as e:\n"
        "        return 'BLOCKED:' + type(e).__name__\n"
        "import asyncio\n"
        "print(asyncio.get_event_loop().run_until_complete(go()))\n"
    )
    result = await run_python_artifact(code, sandbox=sandbox, session_id=sid)
    assert "BLOCKED" in result["payload"]["text"]
    assert "LEAKED" not in result["payload"]["text"]


async def test_arbitrary_network_blocked(sandbox, sid):
    # urllib reaches network only via JS bridge; Pyodide's urllib doesn't
    # actually do raw sockets. Use pyodide.http via a non-allowlisted host.
    code = (
        "from pyodide.http import pyfetch\n"
        "import asyncio\n"
        "async def go():\n"
        "    try:\n"
        "        r = await pyfetch('https://example.com')\n"
        "        return 'LEAKED ' + str(r.status)\n"
        "    except Exception as e:\n"
        "        return 'BLOCKED:' + type(e).__name__\n"
        "print(asyncio.get_event_loop().run_until_complete(go()))\n"
    )
    result = await run_python_artifact(code, sandbox=sandbox, session_id=sid)
    assert "BLOCKED" in result["payload"]["text"]
    assert "LEAKED" not in result["payload"]["text"]
