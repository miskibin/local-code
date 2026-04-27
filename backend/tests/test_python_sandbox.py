"""Pyodide sandbox tests for `python_exec` (replaces subprocess executor).

Slow: each call boots Deno + Pyodide (~3-5 s warm, ~30+ s cold first call
per fresh sessions_dir). Skipped if Deno isn't on PATH so CI without it stays
green. The `python_sandbox` fixture is shared from conftest.
"""

import os
import uuid

import pytest

# Cold first call needs longer than the production default while Pyodide
# downloads + caches packages.
os.environ["PYTHON_SANDBOX_TIMEOUT"] = "180"

from app.artifact_store import run_python_artifact


@pytest.fixture
def sandbox(python_sandbox):
    return python_sandbox


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


async def test_image_artifact(sandbox):
    # Run without session_id: dill.session.dump_session can fail to pickle
    # matplotlib's internal caches and crash the wrapper after the artifact
    # was emitted. Image artifacts inherently end-of-thread anyway.
    code = "import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\nout_image(title='t')\n"
    result = await run_python_artifact(code, sandbox=sandbox, session_id=None)
    assert result["kind"] == "image"
    assert result["payload"]["format"] == "png"
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
    # config used by reset_session points at sandbox's sessions_dir; piggy-back
    # by monkeypatching settings via the same dir.
    from app.config import get_settings
    from app.python_sandbox import reset_session

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


async def test_js_deno_filesystem_escape_blocked(sandbox):
    # Without narrow allow_read, agent could escape via js.Deno.readTextFile.
    # Confirm the narrowed read list raises NotCapable for arbitrary paths.
    # Pyodide runs user code under runPythonAsync, so top-level `await` works.
    # session_id=None: dill can't pickle the imported `js` module reference,
    # which would crash the wrapper after the print() succeeded.
    code = (
        "import js\n"
        "try:\n"
        "    await js.Deno.readTextFile(r'C:/Windows/System32/drivers/etc/hosts')\n"
        "    print('LEAKED')\n"
        "except Exception as e:\n"
        "    print('BLOCKED:' + type(e).__name__)\n"
    )
    result = await run_python_artifact(code, sandbox=sandbox, session_id=None)
    assert "BLOCKED" in result["payload"]["text"]
    assert "LEAKED" not in result["payload"]["text"]


async def test_arbitrary_network_blocked(sandbox):
    # Pyodide's pyfetch goes through Deno's fetch; with allow_net narrowed
    # to package CDNs, arbitrary hosts must fail.
    code = (
        "from pyodide.http import pyfetch\n"
        "try:\n"
        "    r = await pyfetch('https://example.com')\n"
        "    print('LEAKED ' + str(r.status))\n"
        "except Exception as e:\n"
        "    print('BLOCKED:' + type(e).__name__)\n"
    )
    result = await run_python_artifact(code, sandbox=sandbox, session_id=None)
    assert "BLOCKED" in result["payload"]["text"]
    assert "LEAKED" not in result["payload"]["text"]
