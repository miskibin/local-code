import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
