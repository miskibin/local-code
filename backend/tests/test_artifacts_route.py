import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_artifacts_crud():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedArtifact

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        await s.commit()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "id": "art-1",
                "session_id": "sess-1",
                "kind": "table",
                "title": "Q1 sales",
                "payload": {"rows": [{"a": 1}], "columns": ["a"]},
            }
            r = await ac.post("/artifacts", json=payload)
            assert r.status_code == 200
            assert r.json()["id"] == "art-1"

            r2 = await ac.get("/artifacts")
            assert any(x["id"] == "art-1" for x in r2.json())

            r_dup = await ac.post("/artifacts", json=payload)
            assert r_dup.status_code == 200

            r3 = await ac.delete("/artifacts/art-1")
            assert r3.status_code == 200

            r4 = await ac.get("/artifacts")
            assert all(x["id"] != "art-1" for x in r4.json())

            r5 = await ac.delete("/artifacts/missing")
            assert r5.status_code == 404
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()


@pytest.mark.asyncio
async def test_refresh_route_re_executes_python_source():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedArtifact

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        await s.commit()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "id": "ref-1",
                "kind": "table",
                "title": "stale",
                "payload": {"columns": [], "rows": []},
                "summary": "",
                "source_kind": "python",
                "source_code": "out([{'n': 99}])",
            }
            r = await ac.post("/artifacts", json=payload)
            assert r.status_code == 200, r.text

            r2 = await ac.post("/artifacts/ref-1/refresh")
            assert r2.status_code == 200, r2.text
            body = r2.json()
            assert body["payload"]["rows"] == [{"n": 99}]
            assert body["updated_at"] is not None

            r3 = await ac.get("/artifacts/ref-1")
            assert r3.status_code == 200
            assert r3.json()["payload"]["rows"] == [{"n": 99}]

            r4 = await ac.post("/artifacts/missing/refresh")
            assert r4.status_code == 404
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()


@pytest.mark.asyncio
async def test_refresh_route_re_renders_matplotlib_image():
    import base64

    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedArtifact

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        await s.commit()
    code = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.plot([0, 1], [0, 1])\n"
        "out_image()\n"
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post(
                "/artifacts",
                json={
                    "id": "img-1",
                    "kind": "image",
                    "title": "stale",
                    "payload": {"format": "png", "data_b64": "", "caption": None},
                    "summary": "",
                    "source_kind": "python",
                    "source_code": code,
                },
            )
            r = await ac.post("/artifacts/img-1/refresh")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["kind"] == "image"
            raw = base64.b64decode(body["payload"]["data_b64"])
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()


@pytest.mark.asyncio
async def test_get_artifact_route_returns_full_dto():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedArtifact

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        await s.commit()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post(
                "/artifacts",
                json={
                    "id": "g-1",
                    "kind": "text",
                    "title": "t",
                    "payload": {"text": "hi"},
                    "summary": "hi",
                    "source_kind": "text",
                    "source_code": "hi",
                },
            )
            r = await ac.get("/artifacts/g-1")
            assert r.status_code == 200
            body = r.json()
            assert body["source_code"] == "hi"
            assert body["summary"] == "hi"

            r404 = await ac.get("/artifacts/nope")
            assert r404.status_code == 404
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()


@pytest.mark.asyncio
async def test_saved_artifact_persists():
    from sqlmodel import delete, select

    from app.db import async_session, init_db
    from app.models import SavedArtifact

    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        s.add(SavedArtifact(id="x1", kind="image", title="t", payload={"k": 1}))
        await s.commit()
    async with async_session() as s:
        rows = (await s.execute(select(SavedArtifact))).scalars().all()
    try:
        assert any(r.id == "x1" and r.payload == {"k": 1} for r in rows)
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()
