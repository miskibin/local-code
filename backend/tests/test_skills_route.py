import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def _write_skill(root: Path, name: str, description: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nplaybook body\n",
        encoding="utf-8",
    )


@pytest.fixture
def skills_dir(tmp_path: Path):
    _write_skill(tmp_path, "data-analysis", "do data")
    _write_skill(tmp_path, "creating-vis", "make charts")
    os.environ["SKILLS_DIR"] = str(tmp_path)
    from app.config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_skills_default_enabled(skills_dir):
    from app.db import init_db
    from app.main import create_app

    app = create_app()
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/skills")
    assert r.status_code == 200
    body = r.json()
    names = sorted(s["name"] for s in body)
    assert names == ["creating-vis", "data-analysis"]
    assert all(s["enabled"] is True for s in body)


@pytest.mark.asyncio
async def test_patch_skill_persists(skills_dir):
    from app.db import init_db
    from app.main import create_app

    app = create_app()
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.patch("/skills/data-analysis", json={"enabled": False})
        assert r.status_code == 200
        assert r.json()["enabled"] is False

        r2 = await ac.get("/skills")
        by_name = {s["name"]: s for s in r2.json()}
        assert by_name["data-analysis"]["enabled"] is False
        assert by_name["creating-vis"]["enabled"] is True


@pytest.mark.asyncio
async def test_patch_unknown_skill_404(skills_dir):
    from app.db import init_db
    from app.main import create_app

    app = create_app()
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.patch("/skills/does-not-exist", json={"enabled": False})
    assert r.status_code == 404
