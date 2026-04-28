"""Adversarial tests for python_exec sandbox.

Two layers under test:
- AST validator rejects dangerous imports / calls before subprocess starts
  (`ValueError`, surfaced as `ToolException`).
- Audit hook in the subprocess preamble blocks file writes, project-file /
  DB reads, network, and subprocess at runtime (`PermissionError` →
  non-zero exit → `ToolException`).
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
async def _init_db():
    from app.db import init_db

    await init_db()


async def _invoke(code: str):
    from app.tools.python_exec import python_exec

    return await python_exec.ainvoke(
        dict(type="tool_call", id="sb1", name="python_exec", args={"code": code})
    )


@pytest.mark.parametrize(
    "code",
    [
        "import sqlite3",
        "import sqlalchemy",
        "from sqlite3 import connect",
        "import socket",
        "import urllib.request",
        "import requests",
        "import httpx",
        "import subprocess",
        "import ctypes",
        "import importlib",
    ],
)
async def test_blocked_imports_rejected_at_ast(code):
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "blocked" in msg.content.lower()


@pytest.mark.parametrize(
    "code",
    [
        '__import__("sqlite3")',
        'exec("x=1")',
        'eval("1+1")',
        'compile("x=1", "<x>", "exec")',
    ],
)
async def test_blocked_callables_rejected_at_ast(code):
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "blocked" in msg.content.lower()


@pytest.mark.parametrize(
    "code",
    [
        'import os; os.system("echo hi")',
        'import os; os.popen("ls")',
        'import os; os.execv("/bin/ls", ["ls"])',
    ],
)
async def test_blocked_os_attrs_rejected_at_ast(code):
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "blocked" in msg.content.lower()


async def test_runtime_blocks_writing_outside_sandbox(tmp_path):
    # AST has no opinion on `open()` calls — audit hook is the gate. tmp_path
    # is the pytest tmp dir, which is OUTSIDE the per-run sandbox cwd
    # (a different mkdtemp under the OS temp root), so this must be blocked.
    target = tmp_path / "lc_sandbox_breakout"
    code = f'open({str(target)!r}, "w").write("x")'
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "sandbox" in msg.content.lower()


async def test_runtime_blocks_reading_project_file():
    # Try to exfiltrate a project source file.
    target = PROJECT_ROOT / "CLAUDE.md"
    code = f'open({str(target)!r}, "r").read()'
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "sandbox" in msg.content.lower()


async def test_runtime_blocks_reading_dot_env(tmp_path):
    target = tmp_path / ".env.fake"
    target.write_text("X=1")
    code = f'open({str(target)!r}, "r").read()'
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "sandbox" in msg.content.lower()


async def test_runtime_blocks_reading_db_file(tmp_path):
    # Even a path with a `.db` basename is rejected before sqlite would touch it.
    target = tmp_path / "lc_fake.db"
    target.write_bytes(b"SQLite format 3\x00")
    code = f'open({str(target)!r}, "rb").read(16)'
    msg = await _invoke(code)
    assert msg.status == "error"
    assert "sandbox" in msg.content.lower()


async def test_writes_inside_sandbox_cwd_succeed():
    # Relative writes resolve to the per-run sandbox cwd, which is allowed.
    code = 'open("ok.txt", "w").write("hi"); out({"wrote": True})'
    msg = await _invoke(code)
    assert msg.status != "error", msg.content


async def test_pandas_smoke_still_works():
    code = (
        "import pandas as pd\n"
        "df = pd.DataFrame([{'n': 1}, {'n': 2}])\n"
        "out(df.reset_index().to_dict('records'))\n"
    )
    msg = await _invoke(code)
    assert msg.status != "error", msg.content
    assert isinstance(msg.artifact, dict)
    assert msg.artifact.get("kind") == "table"


async def test_matplotlib_smoke_still_works():
    code = (
        "import matplotlib.pyplot as plt\n"
        "plt.bar(['a', 'b'], [1, 2])\n"
        "out_image(title='t')\n"
    )
    msg = await _invoke(code)
    assert msg.status != "error", msg.content
    assert msg.artifact.get("kind") == "image"
