import pytest


@pytest.mark.asyncio
async def test_refresh_python_artifact_updates_payload_and_timestamp(chinook_path):
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    from tests.conftest import TEST_OWNER_ID, ensure_test_user

    await ensure_test_user()
    art = await create_artifact(
        owner_id=TEST_OWNER_ID,
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
async def test_refresh_sql_artifact_round_trip(chinook_path):
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    from tests.conftest import TEST_OWNER_ID, ensure_test_user

    await ensure_test_user()
    art = await create_artifact(
        owner_id=TEST_OWNER_ID,
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
async def test_refresh_rejects_artifact_with_no_source(chinook_path):
    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    from tests.conftest import TEST_OWNER_ID, ensure_test_user

    await ensure_test_user()
    art = await create_artifact(
        owner_id=TEST_OWNER_ID,
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
async def test_refresh_python_image_artifact_round_trip(chinook_path):
    import base64

    from app.artifact_store import create_artifact, refresh_artifact
    from app.db import init_db

    await init_db()
    code = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.bar(['a', 'b'], [1, 2])\n"
        "out_image(title='t')\n"
    )
    art = await create_artifact(
        kind="image",
        title="seed",
        payload={"format": "png", "data_b64": "", "caption": None},
        summary="",
        source_kind="python",
        source_code=code,
    )
    pre = art.updated_at
    fresh = await refresh_artifact(art.id)
    assert fresh.kind == "image"
    assert fresh.payload["format"] == "png"
    raw = base64.b64decode(fresh.payload["data_b64"])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert fresh.updated_at >= pre
