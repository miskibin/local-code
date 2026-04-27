from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from loguru import logger

_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_MAX_NAME = 64
_MAX_DESCRIPTION = 1024
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class SkillInfo:
    name: str
    description: str
    path: str
    body: str


def _parse(skill_md: Path, dir_name: str) -> SkillInfo | None:  # noqa: PLR0911
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"skill read failed {skill_md}: {e}")
        return None

    m = _FRONTMATTER_RE.match(content)
    if not m:
        logger.warning(f"skill {skill_md} missing YAML frontmatter")
        return None
    try:
        front = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        logger.warning(f"skill {skill_md} invalid YAML: {e}")
        return None
    if not isinstance(front, dict):
        logger.warning(f"skill {skill_md} frontmatter is not a mapping")
        return None

    name = str(front.get("name", "")).strip()
    description = str(front.get("description", "")).strip()
    if not name or not description:
        logger.warning(f"skill {skill_md} missing name or description")
        return None
    if len(name) > _MAX_NAME or not _NAME_RE.match(name):
        logger.warning(f"skill {skill_md} name '{name}' invalid")
        return None
    if name != dir_name:
        logger.warning(f"skill {skill_md} name '{name}' must match dir '{dir_name}'")
        return None
    if len(description) > _MAX_DESCRIPTION:
        description = description[:_MAX_DESCRIPTION]

    return SkillInfo(
        name=name,
        description=description,
        path=f"/{name}/SKILL.md",
        body=content,
    )


def discover_skills(skills_dir: str | Path) -> list[SkillInfo]:
    root = Path(skills_dir)
    if not root.is_dir():
        return []
    out: list[SkillInfo] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            continue
        info = _parse(skill_md, child.name)
        if info is not None:
            out.append(info)
    return out


def filter_enabled(skills: list[SkillInfo], flags: dict[str, bool]) -> list[SkillInfo]:
    """Keep skills whose flag is True (or absent — default enabled)."""
    return [s for s in skills if flags.get(s.name, True)]
