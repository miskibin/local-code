---
name: creating-vis
description: Chart-type selection guide and matplotlib recipes for non-trivial plots. Load when the user asks for a chart that's not a basic bar (stacked, multi-axis, time series, etc.).
---

# Visualisation recipes

The core conventions (`out_image`, `out(...to_dict("records"))`,
`read_artifact`, no markdown plots) are already in your main instructions.
This skill is just chart-type guidance and worked recipes.

## Choosing a chart type

| Question shape | Chart |
|---|---|
| Compare values across categories | bar (horizontal if labels long) |
| Compare composition across categories | stacked bar |
| Show distribution | histogram or box |
| Trend over time | line |
| Two numeric variables | scatter |
| Part-of-whole, single category | pie (use sparingly — bar is usually better) |

Default to a bar chart unless the data shape clearly says otherwise. Long
labels → use horizontal bar (`barh`).

## Recipe: stacked bar (top-N × dimension)

```python
import matplotlib.pyplot as plt

customers = read_artifact("art_a")  # CustomerId, FirstName, LastName, TotalSpend
genre = read_artifact("art_b")      # CustomerId, Genre, Spend

pivot = (
    genre
    .merge(customers[["CustomerId", "FirstName", "LastName"]], on="CustomerId")
    .assign(name=lambda d: d["FirstName"] + " " + d["LastName"])
    .pivot_table(index="name", columns="Genre", values="Spend", aggfunc="sum", fill_value=0)
)

# Order rows by total spend so the chart reads top-down.
pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]

fig, ax = plt.subplots(figsize=(9, 5))
pivot.plot(kind="barh", stacked=True, ax=ax)
ax.set_xlabel("Spend")
ax.set_title("Genre mix per top-10 customer")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
out_image(fig, title="Genre mix per top-10 customer")
```

## Recipe: time series

```python
import matplotlib.pyplot as plt

df = read_artifact("art_…").assign(
    period=lambda d: pd.to_datetime(d["InvoiceDate"]).dt.to_period("M").dt.to_timestamp()
)
totals = df.groupby("period")["Total"].sum().reset_index()

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(totals["period"], totals["Total"])
ax.set_title("Monthly revenue")
fig.autofmt_xdate()
fig.tight_layout()
out_image(fig, title="Monthly revenue")
```

## Style notes

- Default matplotlib palette is fine; don't override colors unless asked.
- Always set `ax.set_title(...)` AND pass `title=` to `out_image` — the
  chip uses the latter.
- Always call `fig.tight_layout()` before `out_image` so labels aren't
  clipped.
- For >10 categories, group the long tail into "Other" before plotting.
