from langchain_core.tools import tool


@tool
def fake_tool(x: int) -> int:
    """double it"""
    return x * 2


def test_active_tools_filters_by_flag():
    from app.tool_registry import active_tools
    flags = {"fake_tool": False}
    assert active_tools([fake_tool], [], flags) == []
    assert active_tools([fake_tool], [], {"fake_tool": True}) == [fake_tool]
    # missing flag defaults to enabled
    assert active_tools([fake_tool], [], {}) == [fake_tool]


def test_discover_tools_returns_basetool_instances():
    from langchain_core.tools import BaseTool

    from app.tool_registry import discover_tools
    found = discover_tools()
    assert all(isinstance(t, BaseTool) for t in found)
