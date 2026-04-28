from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

_BULLET_MAX_CHARS = 140


class TitleSlide(BaseModel):
    type: Literal["title"]
    title: str = Field(max_length=80)
    subtitle: str | None = Field(default=None, max_length=120)


class SectionSlide(BaseModel):
    type: Literal["section"]
    title: str = Field(max_length=60)
    eyebrow: str | None = Field(default=None, max_length=40)


class BulletsSlide(BaseModel):
    type: Literal["bullets"]
    title: str = Field(max_length=70)
    bullets: list[str] = Field(min_length=1, max_length=5)

    @field_validator("bullets")
    @classmethod
    def _check_bullet_length(cls, v: list[str]) -> list[str]:
        for i, b in enumerate(v):
            if len(b) > _BULLET_MAX_CHARS:
                raise ValueError(f"bullet {i} exceeds {_BULLET_MAX_CHARS} chars")
        return v


class ChartSlide(BaseModel):
    type: Literal["chart"]
    title: str = Field(max_length=70)
    artifact_id: str
    caption: str | None = Field(default=None, max_length=200)


class TableSlide(BaseModel):
    type: Literal["table"]
    title: str = Field(max_length=70)
    artifact_id: str
    caption: str | None = Field(default=None, max_length=200)
    max_rows: int = Field(default=8, ge=2, le=20)


class ConclusionSlide(BaseModel):
    type: Literal["conclusion"]
    title: str = Field(default="Key takeaways", max_length=70)
    bullets: list[str] = Field(min_length=1, max_length=5)
    cta: str | None = Field(default=None, max_length=120)

    @field_validator("bullets")
    @classmethod
    def _check_bullet_length(cls, v: list[str]) -> list[str]:
        for i, b in enumerate(v):
            if len(b) > _BULLET_MAX_CHARS:
                raise ValueError(f"bullet {i} exceeds {_BULLET_MAX_CHARS} chars")
        return v


Slide = Annotated[
    TitleSlide | SectionSlide | BulletsSlide | ChartSlide | TableSlide | ConclusionSlide,
    Field(discriminator="type"),
]


class DeckSpec(BaseModel):
    title: str = Field(max_length=100)
    author: str | None = Field(default=None, max_length=80)
    date: str | None = Field(default=None, max_length=40)
    slides: list[Slide] = Field(min_length=1, max_length=30)
