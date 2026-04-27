from pathlib import Path

from app.skills_registry import SkillInfo, discover_skills, filter_enabled


def _write_skill(root: Path, name: str, frontmatter: str, body: str = "body\n") -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def test_discover_happy_path(tmp_path: Path):
    _write_skill(tmp_path, "data-analysis", "name: data-analysis\ndescription: do data")
    _write_skill(tmp_path, "creating-vis", "name: creating-vis\ndescription: make charts")

    skills = discover_skills(tmp_path)
    names = sorted(s.name for s in skills)
    assert names == ["creating-vis", "data-analysis"]
    by_name = {s.name: s for s in skills}
    assert by_name["data-analysis"].description == "do data"
    assert by_name["data-analysis"].path == "/data-analysis/SKILL.md"
    assert "body" in by_name["data-analysis"].body


def test_discover_skips_missing_frontmatter(tmp_path: Path):
    d = tmp_path / "broken"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter here", encoding="utf-8")
    assert discover_skills(tmp_path) == []


def test_discover_skips_name_dir_mismatch(tmp_path: Path):
    _write_skill(tmp_path, "wrongdir", "name: actual-name\ndescription: x")
    assert discover_skills(tmp_path) == []


def test_discover_skips_invalid_name_format(tmp_path: Path):
    _write_skill(tmp_path, "Bad_Name", "name: Bad_Name\ndescription: x")
    assert discover_skills(tmp_path) == []


def test_discover_missing_dir_returns_empty(tmp_path: Path):
    assert discover_skills(tmp_path / "nope") == []


def test_filter_enabled_defaults_to_true():
    skills = [
        SkillInfo(name="a", description="x", path="/a/SKILL.md", body=""),
        SkillInfo(name="b", description="x", path="/b/SKILL.md", body=""),
    ]
    # No flags -> all enabled.
    assert filter_enabled(skills, {}) == skills
    # One off.
    assert filter_enabled(skills, {"a": False}) == [skills[1]]
    # Explicit on.
    assert filter_enabled(skills, {"a": True, "b": True}) == skills
