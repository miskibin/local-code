import pytest

pytestmark = pytest.mark.skip(
    reason="Deno unavailable in CI/local - sandbox tool requires Deno"
)


@pytest.mark.asyncio
async def test_python_exec_runs_simple_code():
    from app.tools.python_exec import python_exec
    out = await python_exec.ainvoke({"code": "print(2 + 2)"})
    assert "4" in out


@pytest.mark.asyncio
async def test_python_exec_captures_exception():
    from app.tools.python_exec import python_exec
    out = await python_exec.ainvoke({"code": "1/0"})
    assert "ZeroDivisionError" in out or "error" in out.lower()
