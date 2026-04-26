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
async def test_python_exec_emits_chart_artifact():
    from app.tools.python_exec import python_exec

    msg = await python_exec.ainvoke(
        dict(type="tool_call",
            id="t2",
            name="python_exec",
            args={
                "code": (
                    "out({'labels': ['a','b','c'], 'values': [1.0, 2.5, 4.0], "
                    "'title': 'demo'})"
                )
            },
        )
    )
    assert msg.artifact["kind"] == "chart"
    assert msg.artifact["title"] == "demo"
    assert len(msg.artifact["payload"]["data"]) == 3


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
