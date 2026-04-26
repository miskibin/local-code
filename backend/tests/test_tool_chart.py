import pytest


@pytest.mark.asyncio
async def test_chart_consumes_table_artifact_and_records_lineage():
    from app.artifact_store import create_artifact
    from app.db import init_db
    from app.tools.chart import chart

    await init_db()
    table = await create_artifact(
        kind="table",
        title="src",
        payload={
            "columns": [{"key": "label", "label": "label"}, {"key": "n", "label": "n"}],
            "rows": [
                {"label": "a", "n": 1},
                {"label": "b", "n": 4},
                {"label": "c", "n": 9},
            ],
        },
        summary="3 rows",
        source_kind="sql",
        source_code="SELECT 1",
    )
    msg = await chart.ainvoke(
        dict(
            type="tool_call",
            id="c1",
            name="chart",
            args={"artifact_id": table.id, "x": "label", "y": "n", "kind": "bar"},
        )
    )
    assert msg.artifact["kind"] == "chart"
    assert msg.artifact["parent_artifact_ids"] == [table.id]
    data = msg.artifact["payload"]["data"]
    assert [d["label"] for d in data] == ["a", "b", "c"]
    assert [d["value"] for d in data] == [1.0, 4.0, 9.0]


@pytest.mark.asyncio
async def test_chart_rejects_unknown_columns():
    from app.artifact_store import create_artifact
    from app.db import init_db
    from app.tools.chart import chart

    await init_db()
    table = await create_artifact(
        kind="table",
        title="src",
        payload={
            "columns": [{"key": "x", "label": "x"}],
            "rows": [{"x": 1}],
        },
        summary="",
        source_kind="sql",
        source_code="",
    )
    msg = await chart.ainvoke(
        dict(
            type="tool_call",
            id="c2",
            name="chart",
            args={"artifact_id": table.id, "x": "x", "y": "missing"},
        )
    )
    assert msg.content.startswith("chart error:")
    assert "missing" in msg.content
    assert msg.artifact == {}
