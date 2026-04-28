from __future__ import annotations

import asyncio
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import ToolException, tool
from pydantic import ValidationError

from app.artifact_store import (
    build_and_persist_tool_artifact,
    get_artifact,
)
from app.config import get_settings
from app.schemas.pptx import DeckSpec
from app.services.pptx_render import PptxRenderError, render_deck
from app.utils import now_utc


def _new_pptx_artifact_id() -> str:
    return "art_" + now_utc().strftime("%Y%m%d%H%M%S%f")[:18]


@tool(response_format="content_and_artifact")
async def generate_pptx(deck: DeckSpec, config: RunnableConfig) -> tuple[str, dict]:
    """Generate a PowerPoint deck from a structured spec, return a downloadable artifact.

    Use when the user asks for a deck / presentation / "summarise this for
    stakeholders" / "wrap this analysis up". Reference existing artifacts
    (charts, tables) by id — see the pptx-deck skill for full guidance.

    Slide types (each entry in `deck.slides`):
    - {type: "title", title, subtitle?}
    - {type: "section", title, eyebrow?}
    - {type: "bullets", title, bullets: [str, ...] (1-5)}
    - {type: "chart", title, artifact_id, caption?}     # artifact must be image
    - {type: "table", title, artifact_id, caption?, max_rows?}  # artifact must be table
    - {type: "conclusion", title?, bullets: [str, ...] (1-5), cta?}

    Hard limits enforced (titles, bullet counts, char lengths) — if you
    exceed them the tool raises and you must shorten and retry.

    AFTER the call: in your final reply, link the resulting deck with
    `[deck title](artifact:art_xxx)` markdown. Without that syntax the UI
    shows no download card.
    """
    settings = get_settings()
    template_path = Path(settings.pptx_template_path)
    decks_dir = Path(settings.decks_dir)

    artifact_id = _new_pptx_artifact_id()
    out_path = decks_dir / f"{artifact_id}.pptx"

    artifact_cache: dict[str, object] = {}

    async def _async_lookup(aid: str):
        if aid in artifact_cache:
            return artifact_cache[aid]
        row = await get_artifact(aid)
        artifact_cache[aid] = row
        return row

    referenced_ids: list[str] = []
    for s in deck.slides:
        aid = getattr(s, "artifact_id", None)
        if aid:
            referenced_ids.append(aid)
    for aid in referenced_ids:
        await _async_lookup(aid)

    def _sync_lookup(aid: str):
        return artifact_cache.get(aid)

    try:
        path = await asyncio.to_thread(render_deck, deck, template_path, _sync_lookup, out_path)
    except PptxRenderError as e:
        raise ToolException(f"pptx render error: {e}") from e
    except ValidationError as e:
        raise ToolException(f"pptx spec invalid: {e}") from e

    size_bytes = path.stat().st_size
    safe_filename = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in deck.title)
    safe_filename = safe_filename.strip().replace(" ", "_") or "deck"
    payload = {
        "path": str(path),
        "filename": f"{safe_filename}.pptx",
        "slide_count": len(deck.slides),
        "size_bytes": size_bytes,
        "deck_title": deck.title,
    }
    parent_ids = sorted({aid for aid in referenced_ids if aid in artifact_cache})
    summary = f"Created {len(deck.slides)}-slide deck '{deck.title}' ({size_bytes // 1024} KB)."
    result = {
        "kind": "pptx",
        "title": deck.title,
        "payload": payload,
        "summary": summary,
    }
    return await build_and_persist_tool_artifact(
        result=result,
        source_kind="pptx",
        source_code=deck.model_dump_json(),
        config=config,
        parent_artifact_ids=parent_ids,
    )


generate_pptx.handle_tool_error = True
