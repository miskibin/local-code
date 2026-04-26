import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _chinook_path():
    here = Path(__file__).resolve().parents[1] / "data" / "chinook.db"
    os.environ["CHINOOK_DB_PATH"] = str(here)
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_refresh_python_artifact_updates_payload_and_timestamp():
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    art = await create_artifact(
        kind="table",
        title="seed",
        payload={"columns": [{"key": "n", "label": "n"}], "rows": [{"n": 1}]},
        summary="1 row",
        source_kind="python",
        source_code="out([{'n': 42}])",
    )
    pre = art.updated_at
    fresh = await refresh_artifact(art.id)
    assert fresh.payload["rows"] == [{"n": 42}]
    assert fresh.updated_at >= pre


@pytest.mark.asyncio
async def test_refresh_sql_artifact_round_trip():
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    art = await create_artifact(
        kind="table",
        title="seed",
        payload={"columns": [], "rows": []},
        summary="empty",
        source_kind="sql",
        source_code="SELECT FirstName FROM Customer LIMIT 2",
    )
    fresh = await refresh_artifact(art.id)
    assert fresh.kind == "table"
    assert len(fresh.payload["rows"]) == 2
    assert fresh.payload["columns"][0]["key"] == "FirstName"


@pytest.mark.asyncio
async def test_refresh_rejects_artifact_with_no_source():
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    art = await create_artifact(
        kind="text",
        title="no source",
        payload={"text": "x"},
        summary="x",
        source_kind=None,
        source_code=None,
    )
    with pytest.raises(ValueError):
        await refresh_artifact(art.id)


@pytest.mark.asyncio
async def test_refresh_chart_uses_parent_artifact_id():
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    parent = await create_artifact(
        kind="table",
        title="src",
        payload={
            "columns": [{"key": "x", "label": "x"}, {"key": "y", "label": "y"}],
            "rows": [{"x": "a", "y": 1}, {"x": "b", "y": 2}],
        },
        summary="2 rows",
        source_kind="sql",
        source_code="",
    )
    chart_art = await create_artifact(
        kind="chart",
        title="c",
        payload={"data": []},
        summary="",
        source_kind="chart",
        source_code='{"x":"x","y":"y","kind":"bar"}',
        parent_artifact_ids=[parent.id],
    )
    fresh = await refresh_artifact(chart_art.id)
    assert fresh.kind == "chart"
    assert len(fresh.payload["data"]) == 2
