import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_sessions_crud():
    from sqlmodel import delete

    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import ChatSession

    app = create_app()
    await init_db()
    async with async_session() as s:
        await s.execute(delete(ChatSession))
        await s.commit()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/sessions", json={"id": "s1", "title": "first"})
            assert r.status_code == 200

            r2 = await ac.get("/sessions")
            assert any(x["id"] == "s1" for x in r2.json())

            r3 = await ac.delete("/sessions/s1")
            assert r3.status_code == 200

            r4 = await ac.get("/sessions")
            assert all(x["id"] != "s1" for x in r4.json())
    finally:
        async with async_session() as s:
            await s.execute(delete(ChatSession))
            await s.commit()
