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
        body: "Sum UnitPrice × Quantity per genre on chinook.db and plot the top 10 as a horizontal bar chart.",
      },
      {
        tag: "ml",
        title: "Predict high-value invoices",
        body: "Build one row per invoice from chinook (customer country, prior spend, basket size, time features). Label = Total in top quartile. Train logistic regression with a time-based split and report ROC-AUC plus the top 5 features.",
      },
      {
        tag: "cohort",
        title: "Cohort retention heatmap",
        body: "Bucket customers by first-purchase month and compute month-over-month repeat rate. Render as a triangular heatmap.",
      },
      {
        tag: "forecast",
        title: "Monthly revenue + trend",
        body: "Aggregate invoices by month, fit a linear trend, and plot actual vs. fitted with a 3-month rolling-mean overlay.",
      },
    ],
  },
  {
    num: "02",
    label: "Build",
    prompts: [
      {
        tag: "deck",
        title: "Wrap analysis into a deck",
        body: "Pull top-5 genres and top-10 customers from chinook, plot each, then assemble a 5-slide pptx (title, two charts, table, conclusion) and link it for download.",
      },
      {
        tag: "email",
        title: "Draft a weekly recap email",
        body: "Compute last 30 days revenue, top-3 selling tracks, and YoY change from chinook, then draft an email recap to me with the result table attached.",
      },
      {
        tag: "csv",
        title: "Profile an uploaded CSV",
        body: "I'll attach a CSV. Read its schema, then compute per-column null counts, distinct counts, and basic numeric stats. Return one summary table.",
      },
      {
        tag: "diff",
        title: "Compare two query snapshots",
        body: "Run two SQL queries that share a key column, then diff them: rows added, removed, and changed. Output one combined table.",
      },
    ],
  },
  {
    num: "03",
    label: "Explore",
    prompts: [
      {
        tag: "web",
        title: "Summarize a live page",
        body: "Fetch https://news.ycombinator.com and list the top 5 stories with title, points, and a one-line takeaway each.",
      },
      {
        tag: "schema",
        title: "Map the chinook schema",
        body: "List every chinook table with columns, types, primary keys, and foreign-key links. Render as a markdown ER overview.",
      },
      {
        tag: "quiz",
        title: "Pick a chart with me",
        body: "I want to highlight a revenue trend. Ask me — line vs. bar vs. area — then plot the winner from monthly chinook revenue.",
      },
      {
        tag: "anomaly",
        title: "Flag weird invoices",
        body: "Scan Invoice and InvoiceLine for outliers — zero totals, missing customers, unit prices far from the per-track median. Return a flagged-rows table with reasons.",
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
