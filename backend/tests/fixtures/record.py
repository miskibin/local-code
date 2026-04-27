"""Manual capture CLI for LangChain chat-model chunks.

NOT invoked by pytest. Run by a maintainer with API keys when chunk shapes
might have drifted (after a LangChain / Gemini / Ollama upgrade) or to seed
new fixtures:

    cd backend
    GOOGLE_API_KEY=... uv run python tests/fixtures/record.py \\
        --provider gemini-flash \\
        --prompt sql_then_chart

Each prompt slug corresponds to a hand-curated message list defined in
`PROMPT_SETS` below — short, deterministic flows that exercise the chunk
shapes the streamer must handle (str content, list[dict] content,
tool_call_chunks, response_metadata with finish_reason, multiblock
signed-response).

Each captured chunk is validated against `schema.RecordedChunk` BEFORE write
— `extra="forbid"` means an upstream addition (e.g. a new top-level field on
AIMessageChunk) makes the capture itself fail loudly. That's the gate. Don't
silently expand the schema to make capture pass; investigate the new field
and update the streamer + schema together.

Output: one JSONL per `(provider, prompt)` under
`backend/tests/fixtures/recorded/<provider>/<prompt>.jsonl`. First line is
`FixtureFile` metadata; remaining lines are `RecordedChunk`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessageChunk, BaseMessage

# `tests/fixtures/record.py` -> `tests/fixtures` on sys.path so `schema` imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import (
    ContentBlock,
    FixtureFile,
    RecordedChunk,
    ResponseMetadata,
    ToolCallChunkShape,
    ToolCallShape,
    UsageMetadata,
)

PROMPT_SETS: dict[str, list[tuple[str, str]]] = {
    # Plain text reply — exercises str content path.
    "short_text": [("user", "Reply with the single word: hello.")],
    # Tool-calling reply — exercises tool_call_chunks path.
    "sql_then_chart": [
        (
            "user",
            "Use the sql tool with query 'SELECT 1 AS one' then summarise the result.",
        ),
    ],
}


def _block_to_recorded(content) -> str | list[ContentBlock]:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[ContentBlock] = []
        for c in content:
            if isinstance(c, dict):
                out.append(ContentBlock(**c))
            else:
                # Stringify unknown shape and surface in `text`.
                out.append(ContentBlock(type=None, text=str(c)))
        return out
    return str(content)


def _chunk_to_recorded(chunk) -> RecordedChunk:
    kind = type(chunk).__name__
    if kind not in {"AIMessageChunk", "AIMessage", "ToolMessage"}:
        raise ValueError(
            f"unsupported chunk kind {kind!r}; extend the shadow schema before recording new types"
        )
    rmd = getattr(chunk, "response_metadata", None) or {}
    umd = getattr(chunk, "usage_metadata", None)
    return RecordedChunk(
        kind=kind,
        content=_block_to_recorded(getattr(chunk, "content", "")),
        tool_call_chunks=[
            ToolCallChunkShape(**tcc) for tcc in (getattr(chunk, "tool_call_chunks", None) or [])
        ],
        tool_calls=[ToolCallShape(**tc) for tc in (getattr(chunk, "tool_calls", None) or [])],
        response_metadata=ResponseMetadata(**rmd),
        usage_metadata=UsageMetadata(**umd) if isinstance(umd, dict) else None,
    )


async def _capture(provider: str, prompt_slug: str) -> Path:
    if prompt_slug not in PROMPT_SETS:
        raise SystemExit(f"unknown prompt slug {prompt_slug!r}; pick from {list(PROMPT_SETS)!r}")
    messages: list[BaseMessage | tuple[str, str]] = list(PROMPT_SETS[prompt_slug])

    if provider == "gemini-flash":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not os.environ.get("GOOGLE_API_KEY"):
            raise SystemExit("GOOGLE_API_KEY required for gemini-flash capture")
        model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=os.environ["GOOGLE_API_KEY"])
    elif provider == "ollama-gemma":
        from langchain_ollama import ChatOllama

        model_name = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = ChatOllama(model=model_name, base_url=base_url)
    else:
        raise SystemExit(f"unsupported provider {provider!r}")

    chunks: list[RecordedChunk] = []
    async for chunk in llm.astream(messages):
        if not isinstance(chunk, AIMessageChunk):
            # We don't currently capture non-AIMessageChunk events from
            # `llm.astream`. If that changes, extend `_chunk_to_recorded`.
            continue
        chunks.append(_chunk_to_recorded(chunk))

    if not chunks:
        raise SystemExit(
            f"no chunks captured for provider={provider!r} prompt={prompt_slug!r}; "
            "either the model returned nothing or the API call failed"
        )

    meta = FixtureFile(
        provider=provider,
        model=model_name,
        prompt=prompt_slug,
        description=f"Captured stream for prompt={prompt_slug!r}",
        captured_at=datetime.now(UTC).isoformat(),
        captured_by="record.py",
        expected_text_nonempty=True,
    )

    out_dir = Path(__file__).resolve().parent / "recorded" / provider
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{prompt_slug}.jsonl"
    with out_path.open("w") as f:
        f.write(meta.model_dump_json() + "\n")
        for c in chunks:
            f.write(c.model_dump_json() + "\n")

    print(f"wrote {len(chunks)} chunks to {out_path}")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--provider", required=True, choices=["gemini-flash", "ollama-gemma"])
    p.add_argument("--prompt", required=True, help=f"prompt slug; one of {list(PROMPT_SETS)}")
    args = p.parse_args()
    asyncio.run(_capture(args.provider, args.prompt))


if __name__ == "__main__":
    main()
