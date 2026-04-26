import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_artifacts_crud():
    from app.main import create_app
    from app.db import init_db, async_session
    from app.models import SavedArtifact
    from sqlmodel import delete

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
async def test_saved_artifact_persists():
    from app.db import init_db, async_session
    from app.models import SavedArtifact
    from sqlmodel import delete, select

    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedArtifact))
        s.add(SavedArtifact(id="x1", kind="chart", title="t", payload={"k": 1}))
        await s.commit()
    async with async_session() as s:
        rows = (await s.execute(select(SavedArtifact))).scalars().all()
    try:
        assert any(r.id == "x1" and r.payload == {"k": 1} for r in rows)
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedArtifact))
            await s.commit()
