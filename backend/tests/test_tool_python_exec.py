import json

import pytest


@pytest.fixture(autouse=True)
async def _init_db():
    from app.db import init_db

    await init_db()


@pytest.mark.asyncio
async def test_python_exec_runs_simple_code():
    from app.tools.python_exec import python_exec

    out = await python_exec.ainvoke({"code": "print(2 + 2)"})
    assert "4" in out


@pytest.mark.asyncio
async def test_python_exec_returns_error_string_on_exception():
    from app.tools.python_exec import python_exec

    out = await python_exec.ainvoke({"code": "1/0"})
    assert out.startswith("error:")
    assert "ZeroDivisionError" in out


@pytest.mark.asyncio
async def test_python_exec_emits_table_artifact_via_tool_call():
    from app.tools.python_exec import python_exec

    msg = await python_exec.ainvoke(
        dict(type="tool_call",
            id="t1",
            name="python_exec",
            args={"code": "out([{'a':1,'b':2},{'a':3,'b':4}])"},
        )
    )
    assert "table 2 rows" in msg.content
    assert msg.content.startswith("art_")
    assert msg.artifact["kind"] == "table"
    assert msg.artifact["payload"]["rows"] == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert msg.artifact["source_kind"] == "python"
    assert "out([" in msg.artifact["source_code"]


@pytest.mark.asyncio
async def test_python_exec_emits_matplotlib_image_artifact():
    import base64

    from app.tools.python_exec import python_exec

    code = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1, 2, 3], [4, 5, 6])\n"
        "out_image(title='demo', caption='line of three')\n"
    )
    msg = await python_exec.ainvoke(
        dict(type="tool_call", id="t2", name="python_exec", args={"code": code})
    )
    assert msg.artifact["kind"] == "image"
    assert msg.artifact["title"] == "demo"
    assert msg.artifact["payload"]["format"] == "png"
    assert msg.artifact["payload"]["caption"] == "line of three"
    raw = base64.b64decode(msg.artifact["payload"]["data_b64"])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert msg.artifact["source_kind"] == "python"
    assert "matplotlib" in msg.artifact["source_code"]


@pytest.mark.asyncio
async def test_python_exec_image_oversize_returns_error():
    from app.tools.python_exec import python_exec

    code = "out({'_image_png_b64': 'A' * (3 * 1024 * 1024)})\n"
    out = await python_exec.ainvoke({"code": code})
    assert out.startswith("error:")
    assert "image too large" in out


@pytest.mark.asyncio
async def test_python_exec_text_fallback():
    from app.tools.python_exec import python_exec

    msg = await python_exec.ainvoke(
        dict(type="tool_call",
            id="t3", name="python_exec", args={"code": "print('hello')"}
        )
    )
    assert msg.artifact["kind"] == "text"
    assert "hello" in msg.artifact["payload"]["text"]
    assert msg.artifact["source_code"] == "print('hello')"


@pytest.mark.asyncio
async def test_python_exec_source_code_preserved_verbatim_for_refresh():
    from app.tools.python_exec import python_exec

    code = "import json\nout([{'k': 1}])"
    msg = await python_exec.ainvoke(
        dict(type="tool_call",id="t4", name="python_exec", args={"code": code})
    )
    assert msg.artifact["source_code"] == code
    parsed = json.dumps(msg.artifact["payload"]["rows"])
    assert "1" in parsed
