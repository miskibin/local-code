---
name: pptx-deck
description: Build a PowerPoint deck (.pptx) from a structured spec. Use when the user asks for a deck, presentation, slide summary, or wants to package an analysis for stakeholders. Embed prior artifacts (charts, tables) by their id.
---

# Building a PowerPoint deck

You have one tool for decks: `generate_pptx`. It takes a JSON spec and
returns a downloadable `.pptx` artifact. The renderer is strict about
character limits and rejects overflowing input — keep things short.

## Surfacing the deck to the user (REQUIRED)

After `generate_pptx` succeeds, your final reply MUST link the deck
artifact using the markdown artifact-link syntax so the UI renders a
download card. Use the artifact id from the tool summary (the `art_...`
prefix). Example final reply:

> Done. [Q3 Sales Review](artifact:art_abc123def456)

Do NOT use a plain link, do NOT embed the file path, do NOT just write
the title in plain text. Without the `artifact:` link, the user sees no
card and cannot download.

## When to use

- User asks for a "deck", "presentation", "slides", "powerpoint", "ppt".
- User says "wrap this up for stakeholders", "make a summary I can share",
  "turn this into slides".
- After an analysis has produced one or more chart/table artifacts and
  the user wants to package them.

Do NOT pre-emptively suggest a deck on every analysis. Only when the user
asks or strongly implies they want one.

## Slide types

Every slide is one of six types. The deck must have at least one slide.
Mix types — a deck of all `bullets` looks AI-generated.

| type | required fields | optional | use when |
|------|-----------------|----------|----------|
| `title` | `title` | `subtitle` | first slide of the deck |
| `section` | `title` | `eyebrow` | divider between major topics |
| `bullets` | `title`, `bullets` (1-5) | — | text-only key points |
| `chart` | `title`, `artifact_id` | `caption` | embed an existing image artifact (matplotlib PNG) |
| `table` | `title`, `artifact_id` | `caption`, `max_rows` (2-20, default 8) | embed an existing table artifact |
| `conclusion` | `bullets` (1-5) | `title`, `cta` | final summary + optional call to action |

## Hard limits (renderer rejects on overflow)

- `deck.title` ≤ 100 chars
- `slide.title` ≤ 60-80 chars (varies by type)
- `bullets[i]` ≤ 140 chars each
- `bullets` length: 1 to 5
- `caption` ≤ 200 chars
- Total slides ≤ 30

## Anti-AI-tell rules

- Vary slide types. A deck of nothing but `bullets` is the dead giveaway.
- Title slides ≤ ~8 words. Long titles read as content slides, not covers.
- Bullets ≤ ~15 words each. If a bullet wraps to 3 lines, split or trim.
- Lead with a `section` slide before each major topic shift.
- Always pair a `chart` slide with a one-sentence takeaway in `caption`
  ("Revenue grew 18% YoY, driven by mid-market"). Never leave a chart
  caption blank or write "see chart".
- End with a `conclusion` slide with 3 bullets — never 5.
- Keep eyebrows short (≤ 3 words, e.g. "Q3 RESULTS", "RISKS").

## Attaching artifacts

Tool calls (sql_query, python_exec) return artifact ids of form
`art_xxxxx…`. The agent sees those ids in tool results. To embed:

```json
{"type": "chart", "title": "Quarterly revenue", "artifact_id": "art_abc123def456",
 "caption": "Q3 grew 18% YoY, mid-market segment leading."}
```

The artifact must already exist — generate the chart/table in a prior
turn (with `python_exec` or `sql_query`), then reference its id here.
Wrong-kind ids (e.g. pointing a `chart` slide at a `kind=table` artifact)
will error. Fix with the right id and retry.

## Example call

```json
{
  "deck": {
    "title": "Q3 Sales Review",
    "author": "Analytics team",
    "date": "2026-04-28",
    "slides": [
      {"type": "title", "title": "Q3 Sales Review", "subtitle": "Top-line, channels, segments"},
      {"type": "section", "title": "Top-line", "eyebrow": "Q3 RESULTS"},
      {"type": "chart", "title": "Quarterly revenue",
       "artifact_id": "art_abc123def456",
       "caption": "Revenue +18% YoY, $42M total."},
      {"type": "table", "title": "Top customers",
       "artifact_id": "art_def456abc789",
       "caption": "Concentration steady; top-5 = 31% of revenue.",
       "max_rows": 8},
      {"type": "bullets", "title": "What changed",
       "bullets": [
         "Mid-market segment +27% on enterprise pricing rollout.",
         "Churn -2pp after onboarding revamp.",
         "EU pipeline +40% but conversion lagging."
       ]},
      {"type": "conclusion", "title": "Takeaways",
       "bullets": [
         "Scale mid-market pricing to EU in Q4.",
         "Invest in EU sales engineering to lift conversion.",
         "Hold churn gains by extending onboarding to existing accounts."
       ],
       "cta": "Decision needed by 2026-05-15."}
    ]
  }
}
```

## Escape hatch

If you genuinely need something the schema does not express (custom
shapes, complex layouts, animations), use `python_exec` with `python-pptx`
directly — read prior artifacts via `read_artifact(id)` and write the
`.pptx` to the sandbox cwd. This is uncommon — try the structured tool
first. The structured tool is faster and produces consistent output.
