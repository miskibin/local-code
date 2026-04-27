import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_tasks_crud_and_export_import():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedTask

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.commit()

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # create-via-import (no id required)
            payload = {
                "id": "",
                "title": "Top customers",
                "description": "Find top N customers by revenue.",
                "variables": [{"name": "top_n", "type": "number", "label": "Top N", "default": 10}],
                "steps": [
                    {
                        "id": "s1",
                        "kind": "code",
                        "title": "Compute",
                        "code": "out([{'n': {{var.top_n}} }])",
                        "output_name": "rows",
                        "output_kind": "rows",
                    }
                ],
            }
            r = await ac.post("/tasks/import", json=payload)
            assert r.status_code == 200, r.text
            created = r.json()
            tid = created["id"]
            assert tid.startswith("tsk_")

            r2 = await ac.get("/tasks")
            assert any(x["id"] == tid for x in r2.json())

            r3 = await ac.get(f"/tasks/{tid}")
            assert r3.status_code == 200
            full = r3.json()
            assert full["title"] == "Top customers"
            assert full["steps"][0]["code"].startswith("out(")

            # update title
            updated = {**full, "title": "Top revenue customers"}
            r4 = await ac.put(f"/tasks/{tid}", json=updated)
            assert r4.status_code == 200
            assert r4.json()["title"] == "Top revenue customers"

            # export strips id
            r5 = await ac.get(f"/tasks/{tid}/export")
            assert r5.status_code == 200
            exported = r5.json()
            assert exported["id"] == ""
            assert exported["title"] == "Top revenue customers"

            # re-import gives a fresh id
            r6 = await ac.post("/tasks/import", json=exported)
            assert r6.status_code == 200
            assert r6.json()["id"] != tid

            # delete
            r7 = await ac.delete(f"/tasks/{tid}")
            assert r7.status_code == 200

            r8 = await ac.get(f"/tasks/{tid}")
            assert r8.status_code == 404

            r9 = await ac.delete("/tasks/missing")
            assert r9.status_code == 404
    finally:
        async with async_session() as s:
            await s.execute(delete(SavedTask))
            await s.commit()


@pytest.mark.asyncio
async def test_update_missing_returns_404():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import SavedTask

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.put(
            "/tasks/nope",
            json={"id": "nope", "title": "x", "variables": [], "steps": []},
        )
        assert r.status_code == 404
