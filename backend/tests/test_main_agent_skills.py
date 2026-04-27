"""Unit tests for StateSkillsMiddleware seeding + prompt injection."""

from app.middleware.skills_state import StateSkillsMiddleware
from app.skills_registry import SkillInfo


def _skill(name: str, body: str = "body") -> SkillInfo:
    return SkillInfo(
        name=name,
        description=f"desc {name}",
        path=f"/{name}/SKILL.md",
        body=body,
    )


def test_state_seed_shape():
    skills = [_skill("data-analysis", "DA body"), _skill("creating-vis", "CV body")]
    mw = StateSkillsMiddleware(skills=skills)
    seed = mw._state_seed()

    assert seed["files"] == {
        "/data-analysis/SKILL.md": {"content": "DA body"},
        "/creating-vis/SKILL.md": {"content": "CV body"},
    }
    assert seed["skills_metadata"] == [
        {
            "name": "data-analysis",
            "description": "desc data-analysis",
            "path": "/data-analysis/SKILL.md",
        },
        {
            "name": "creating-vis",
            "description": "desc creating-vis",
            "path": "/creating-vis/SKILL.md",
        },
    ]


def test_before_agent_returns_seed():
    mw = StateSkillsMiddleware(skills=[_skill("data-analysis")])
    update = mw.before_agent(state={}, runtime=None)
    assert "files" in update
    assert "skills_metadata" in update


def test_prompt_block_lists_skills():
    mw = StateSkillsMiddleware(skills=[_skill("data-analysis"), _skill("creating-vis")])
    block = mw._prompt_block
    assert "data-analysis" in block
    assert "creating-vis" in block
    assert "/data-analysis/SKILL.md" in block
    assert "read_file" in block
