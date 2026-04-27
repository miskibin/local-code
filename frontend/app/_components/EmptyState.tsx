"use client"

import { Fragment } from "react"

type Prompt = {
  tag: string
  title: string
  body: string
}

type Category = {
  num: string
  label: string
  prompts: Prompt[]
}

const CATEGORIES: Category[] = [
  {
    num: "01",
    label: "Analyze",
    prompts: [
      {
        tag: "sql + plot",
        title: "Top genres by revenue",
        body: "Join InvoiceLine → Track → Genre on chinook.db, sum UnitPrice × Quantity per genre, then plot the top 10 as a horizontal bar chart with matplotlib.",
      },
      {
        tag: "cohort",
        title: "Customer cohort retention",
        body: "Bucket customers by their first-purchase month, then compute month-over-month repeat-purchase rate. Render the result as a triangular heatmap.",
      },
      {
        tag: "rfm",
        title: "Top customers (RFM)",
        body: "Score every customer on Recency, Frequency, Monetary using the Invoice table. Return the top 20 with their country and a stacked bar of R/F/M.",
      },
      {
        tag: "forecast",
        title: "Monthly revenue + trend",
        body: "Aggregate invoices by month, fit a simple linear trend, and plot actual vs. fitted with a 3-month rolling average overlay.",
      },
    ],
  },
  {
    num: "02",
    label: "Build",
    prompts: [
      {
        tag: "etl",
        title: "Clean & dedupe a CSV",
        body: "Take a messy CSV: normalize column names to snake_case, strip whitespace, parse dates, drop exact duplicates, and report a before/after row-count diff plus a cleaned table artifact.",
      },
      {
        tag: "api",
        title: "Wrap a query as an endpoint",
        body: "Pick one of my SQL queries and write a minimal FastAPI route that runs it against chinook.db and returns JSON. Include a sample curl call and a pytest covering the happy path.",
      },
      {
        tag: "pipeline",
        title: "Schedule a nightly refresh",
        body: "Sketch a Python script + cron entry that re-runs my top-genres query every night at 2am, writes results to a `daily_genres` table, and logs row counts.",
      },
      {
        tag: "notebook",
        title: "Spin up a starter notebook",
        body: "Generate a Python notebook outline for chinook.db: load tables, compute revenue / customers / top tracks KPIs, and produce three exploratory charts. Output the cells as runnable code.",
      },
    ],
  },
  {
    num: "03",
    label: "Explore",
    prompts: [
      {
        tag: "schema",
        title: "Map the schema",
        body: "Inspect chinook.db: list every table with column names, types, primary keys, and foreign-key relationships. Render as a markdown ER-style overview I can paste into docs.",
      },
      {
        tag: "anomaly",
        title: "Flag weird rows",
        body: "Scan the Invoice and InvoiceLine tables for outliers: zero-total invoices, missing customers, future BillingDates, or unit prices far from the median for that track. Return a flagged-rows table with reasons.",
      },
      {
        tag: "profile",
        title: "Profile a single table",
        body: "Ask me which chinook table to profile, then return: row count, per-column null counts, distinct counts, top 5 values per column, and basic numeric stats. Show the result as a single summary table.",
      },
      {
        tag: "diff",
        title: "Compare two snapshots",
        body: "Given two query results with the same key column, diff them: rows added, rows removed, and rows where any non-key column changed. Output an added/removed/changed table.",
      },
    ],
  },
]

const TOTAL_PROMPTS = CATEGORIES.reduce((n, c) => n + c.prompts.length, 0)

const MONO = "var(--font-mono)"

export function EmptyState({
  onPick,
}: {
  onPick: (suggestion: string) => void
}) {
  return (
    <div
      className="mx-auto flex w-full flex-col justify-center"
      style={{ maxWidth: 860, gap: 18, minHeight: "calc(100dvh - 220px)" }}
    >
      <StatusBar count={TOTAL_PROMPTS} />

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div
          style={{
            color: "var(--ink)",
            fontSize: 26,
            letterSpacing: "-0.01em",
            fontWeight: 500,
          }}
        >
          <span style={{ color: "var(--ink-3)", marginRight: 8 }}>&gt;</span>
          What should we dig into?
        </div>
        <div style={{ color: "var(--ink-3)", fontSize: 13 }}>
          Pick a starting point below, or type a question of your own.
        </div>
      </div>

      <PromptGrid onPick={onPick} />

      <Tip />
    </div>
  )
}

function StatusBar({ count }: { count: number }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontFamily: MONO,
        fontSize: 10.5,
        letterSpacing: ".08em",
        textTransform: "uppercase",
        color: "var(--ink-3)",
        paddingBottom: 6,
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
        <span
          aria-hidden
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--accent)",
            display: "inline-block",
          }}
        />
        Session ready
      </span>
      <span>{count} prompts</span>
    </div>
  )
}

function PromptGrid({ onPick }: { onPick: (s: string) => void }) {
  const last = CATEGORIES.length - 1
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(112px, auto) 1fr 1fr",
        border: "1px solid var(--border)",
      }}
    >
      {CATEGORIES.map((cat, ci) => {
        const isLastCat = ci === last
        return (
          <Fragment key={cat.num}>
            <div
              style={{
                gridRow: "span 2",
                padding: "16px 18px",
                borderRight: "1px solid var(--border)",
                borderBottom: !isLastCat
                  ? "1px solid var(--border)"
                  : undefined,
                background: "var(--bg-soft)",
                display: "flex",
                flexDirection: "column",
                gap: 6,
                fontFamily: MONO,
                fontSize: 11,
                letterSpacing: ".08em",
                textTransform: "uppercase",
              }}
            >
              <div style={{ color: "var(--ink-4)" }}>{cat.num}</div>
              <div style={{ color: "var(--ink-2)" }}>{cat.label}</div>
            </div>

            {cat.prompts.map((p, i) => {
              const isRight = i % 2 === 1
              const isBottom = i >= 2
              return (
                <PromptCell
                  key={p.tag}
                  prompt={p}
                  onPick={onPick}
                  borderRight={!isRight}
                  borderBottom={!(isBottom && isLastCat)}
                />
              )
            })}
          </Fragment>
        )
      })}
    </div>
  )
}

function PromptCell({
  prompt,
  onPick,
  borderRight,
  borderBottom,
}: {
  prompt: Prompt
  onPick: (s: string) => void
  borderRight: boolean
  borderBottom: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => onPick(prompt.body)}
      title={prompt.body}
      className="text-left transition"
      style={{
        background: "transparent",
        border: 0,
        borderRight: borderRight ? "1px solid var(--border)" : undefined,
        borderBottom: borderBottom ? "1px solid var(--border)" : undefined,
        padding: "14px 16px",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        minHeight: 72,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 10.5,
          letterSpacing: ".08em",
          textTransform: "uppercase",
          color: "var(--ink-4)",
        }}
      >
        {prompt.tag}
      </span>
      <span
        style={{
          fontSize: 14,
          color: "var(--ink)",
          fontWeight: 500,
          lineHeight: 1.35,
        }}
      >
        <span style={{ color: "var(--ink-3)", marginRight: 6 }}>&gt;</span>
        {prompt.title}
      </span>
    </button>
  )
}

function Tip() {
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 11,
        letterSpacing: ".04em",
        color: "var(--ink-3)",
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      <span
        style={{
          textTransform: "uppercase",
          letterSpacing: ".1em",
          color: "var(--ink-4)",
        }}
      >
        Tip
      </span>
      <span style={{ color: "var(--ink-4)" }}>·</span>
      <span>
        Click any prompt to load it into the composer, or attach a file with{" "}
        <span
          aria-hidden
          style={{
            display: "inline-flex",
            width: 16,
            height: 16,
            alignItems: "center",
            justifyContent: "center",
            border: "1px solid var(--border-strong)",
            color: "var(--ink-2)",
            fontSize: 11,
            lineHeight: 1,
            verticalAlign: "middle",
          }}
        >
          +
        </span>{" "}
        to start from your own data.
      </span>
    </div>
  )
}
