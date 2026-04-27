"use client"

const CARDS = [
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
]

export function EmptyState({
  onPick,
}: {
  onPick: (suggestion: string) => void
}) {
  return (
    <div className="flex h-[60dvh] flex-col items-center justify-center gap-5 px-4">
      <div
        className="flex items-center gap-2"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          color: "var(--ink-3)",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--accent)",
            boxShadow:
              "0 0 0 3px color-mix(in oklab, var(--accent) 18%, transparent)",
          }}
        />
        <span>chinook.db · gemma-4-e4b · local</span>
      </div>

      <div className="flex flex-col items-center gap-1">
        <div
          className="text-center font-medium"
          style={{
            color: "var(--ink)",
            fontSize: 26,
            letterSpacing: "-0.01em",
          }}
        >
          What should we dig into?
        </div>
        <div
          className="text-center"
          style={{ color: "var(--ink-3)", fontSize: 13 }}
        >
          Pick a starting point, or ask anything.
        </div>
      </div>

      <div
        className="grid w-full grid-cols-2"
        style={{
          maxWidth: 600,
          border: "1px solid var(--border)",
          gap: 0,
        }}
      >
        {CARDS.map((c, i) => (
          <button
            key={c.tag}
            onClick={() => onPick(c.body)}
            className="text-left transition"
            style={{
              background: "transparent",
              border: 0,
              borderRight: i % 2 === 0 ? "1px solid var(--border)" : "0",
              borderBottom: i < 2 ? "1px solid var(--border)" : "0",
              padding: "14px 16px",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--hover)"
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent"
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10.5,
                letterSpacing: ".06em",
                textTransform: "uppercase",
                color: "var(--ink-4)",
              }}
            >
              {c.tag}
            </div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: "var(--ink)",
                marginTop: 6,
              }}
            >
              {c.title}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
