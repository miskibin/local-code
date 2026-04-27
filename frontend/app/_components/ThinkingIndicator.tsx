"use client"

export function ThinkingIndicator() {
  return (
    <div
      className="lc-reveal inline-flex items-center py-1"
      style={{ color: "var(--code-ink)" }}
      aria-live="polite"
      aria-busy="true"
      aria-label="Thinking"
    >
      <span className="lc-dot" aria-hidden />
      <span className="lc-dot" aria-hidden />
      <span className="lc-dot" aria-hidden />
    </div>
  )
}
