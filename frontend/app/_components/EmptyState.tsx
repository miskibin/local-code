"use client";

const SUGGESTIONS = [
  "Plan a 3-day trip to Lisbon",
  "Top 10 customers by revenue from sales.csv",
  "Rust vs Go for a small CLI?",
  "Parse PDF invoices locally",
];

export function EmptyState({
  onPick,
}: {
  onPick: (suggestion: string) => void;
}) {
  return (
    <div className="flex h-[60dvh] flex-col items-center justify-center gap-8 px-4">
      <div
        className="text-center text-[28px] font-medium"
        style={{ color: "var(--ink)", letterSpacing: "-0.01em" }}
      >
        What can I help with?
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-full px-4 py-2 text-[13.5px] transition"
            style={{
              border: "1px solid var(--border)",
              background: "#fff",
              color: "var(--ink)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#fff";
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
