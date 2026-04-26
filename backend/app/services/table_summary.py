"""Single-source LLM-facing summary for table artifacts.

Used by:
  - artifacts upload route (cache result in payload.summary_md at upload time)
  - to_lc_messages converter (inject when a user message references a table)
  - read_table_summary tool (let the agent re-fetch on demand)

Format: YAML metadata + Markdown-KV per-column blocks + small markdown head.
Markdown-KV beat CSV/JSON in the Improving Agents 2025 benchmark; head table
is cheap and gives the model concrete sample values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.models import SavedArtifact

DEFAULT_HEAD_ROWS = 5
DEFAULT_TOP_K = 5
SCAN_NROWS = 200


def _column_block(name: str, series: pd.Series) -> str:
    nulls_pct = round(float(series.isna().mean()) * 100, 1)
    n_unique = int(series.nunique(dropna=True))
    dtype = str(series.dtype)
    parts = [f"- **{name}** ({dtype})", f"  nulls: {nulls_pct}%", f"  unique: {n_unique}"]
    non_null = series.dropna()
    if non_null.empty:
        return "\n".join(parts)
    if pd.api.types.is_numeric_dtype(series):
        parts.append(
            f"  min/max/mean: {non_null.min():g} / {non_null.max():g} / {non_null.mean():g}"
        )
    elif pd.api.types.is_datetime64_any_dtype(series):
        parts.append(f"  min/max: {non_null.min()} / {non_null.max()}")
    else:
        top = non_null.astype(str).value_counts().head(DEFAULT_TOP_K)
        sample = ", ".join(f"{v!r}({c})" for v, c in top.items())
        parts.append(f"  top: {sample}")
    return "\n".join(parts)


def _read_csv(path: Path, *, sample_only: bool) -> pd.DataFrame:
    nrows = SCAN_NROWS if sample_only else None
    return pd.read_csv(path, nrows=nrows)


def build_summary_from_dataframe(
    df: pd.DataFrame,
    *,
    artifact_id: str,
    title: str,
    n_rows_total: int | None = None,
    head_rows: int = DEFAULT_HEAD_ROWS,
) -> str:
    n_rows = n_rows_total if n_rows_total is not None else len(df)
    n_cols = df.shape[1]
    lines = [
        f"## Table: {title} (artifact:{artifact_id})",
        f"rows: {n_rows}, cols: {n_cols}",
        "",
        "### Schema",
    ]
    for col in df.columns:
        lines.append(_column_block(str(col), df[col]))
    lines.append("")
    lines.append(f"### Head (first {min(head_rows, len(df))} rows)")
    lines.append(df.head(head_rows).to_markdown(index=False))
    return "\n".join(lines)


def summarize_csv(
    path: Path | str,
    *,
    artifact_id: str,
    title: str,
) -> dict[str, Any]:
    """Read a CSV and return both the markdown summary and column metadata."""
    p = Path(path)
    sample = _read_csv(p, sample_only=True)
    total = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace")) - 1
    summary_md = build_summary_from_dataframe(
        sample, artifact_id=artifact_id, title=title, n_rows_total=total
    )
    columns = [{"name": str(c), "dtype": str(sample[c].dtype)} for c in sample.columns]
    return {
        "summary_md": summary_md,
        "n_rows": int(total),
        "n_cols": int(sample.shape[1]),
        "columns": columns,
    }


def build_table_summary(artifact: SavedArtifact) -> str:
    """Return cached summary if present; otherwise rebuild from payload.

    For tool-produced table artifacts (rows in payload, no file path), build
    on-the-fly from the in-memory rows.
    """
    payload = artifact.payload or {}
    cached = payload.get("summary_md")
    if cached:
        return cached
    rows = payload.get("rows")
    if isinstance(rows, list) and rows:
        df = pd.DataFrame(rows)
        return build_summary_from_dataframe(df, artifact_id=artifact.id, title=artifact.title)
    path = payload.get("path")
    if path:
        return summarize_csv(path, artifact_id=artifact.id, title=artifact.title)["summary_md"]
    return f"## Table: {artifact.title} (artifact:{artifact.id})\n(no data)"
