# Recorded fixtures

Hand-captured `AIMessageChunk` sequences from real LLM providers, used by
`tests/test_recorded_chunks_replay.py` as a canary against silent drift in
upstream LangChain / Gemini / Ollama chunk shapes.

## Why these exist

The streaming layer (`app/streaming.py`) reads specific fields off
`AIMessageChunk` (`content`, `tool_call_chunks`, `response_metadata.finish_reason`,
`usage_metadata`). We've shipped fixes for several real-world chunk shapes:

- Gemini emits `content` as `list[dict]` blocks (not `str`) — sometimes with
  `extras`/`signature` blocks for signed responses.
- `finish_reason` lives under `response_metadata.finish_reason` for some
  providers and `response_metadata.stop_reason` for others.

Hand-rolled `FakeListChatModel` mocks used in the rest of the test suite
can't catch a *new* upstream shape we don't already know about. These
fixtures are the "ground truth" sample. When LangChain or the underlying
provider changes the chunk shape, re-running `record.py` will either:

1. Fail at validation (because `schema.RecordedChunk` has
   `extra="forbid"` on every modeled field) — surfacing the new field as a
   deliberate review gate.
2. Produce a fixture whose replay through `app/streaming.py` no longer
   yields the expected text — surfacing a behavior regression.

## Layout

```
backend/tests/fixtures/recorded/
├── gemini-flash/
│   ├── short_text.jsonl
│   └── sql_then_chart.jsonl
└── ollama-gemma/
    └── short_text.jsonl
```

Each `.jsonl` is:
- Line 1: `FixtureFile` metadata (provider, model, prompt slug, capture date).
- Line 2+: one `RecordedChunk` per line, in capture order.

Both shapes are defined in `backend/tests/fixtures/schema.py`.

## Re-recording

You need real API access. **Pytest never runs this** — it only loads
existing fixtures.

```bash
cd backend
GOOGLE_API_KEY=… uv run python tests/fixtures/record.py \
    --provider gemini-flash \
    --prompt short_text

OLLAMA_BASE_URL=http://localhost:11434 uv run python tests/fixtures/record.py \
    --provider ollama-gemma \
    --prompt short_text
```

Available prompt slugs: see `PROMPT_SETS` in `record.py`. Add new slugs
there (don't add ad-hoc prompts in this README — keep them in the script
so re-records are reproducible).

## Reviewing fixture diffs

Fixture diffs in PRs are **deliberate review gates**. When you see one:

1. Check whether the upstream change is benign (e.g. provider added a new
   metadata field) or breaking (e.g. `content` shape changed).
2. If breaking: update `app/streaming.py` to handle it AND update
   `schema.py` to model it.
3. If benign but new: extend `schema.py` to allow the field (`extra="allow"`
   on the relevant block, or add a typed field) and re-record.

**Never edit the JSONL files by hand** — they exist to reflect what the
real provider actually emits. Hand edits defeat the whole point.

## Hand-authored seed fixtures

The initial commit ships with hand-authored fixtures (`captured_by:
"hand-authored"` in the metadata) that mirror real shapes the streamer is
known to handle. These are placeholder seeds — the first time a maintainer
runs `record.py` against the relevant provider, the seeds get overwritten
with real captures.
