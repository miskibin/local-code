"use client"

import type { ToolArgsProps, ToolResultProps } from "./types"

/** Default Args renderer — pretty-printed JSON in a monospace block. */
export function DefaultArgs({ args }: ToolArgsProps) {
  return (
    <pre
      className="m-0 rounded-lg px-2.5 py-2 break-words whitespace-pre-wrap"
      style={{
        background: "var(--bg-soft)",
        fontFamily: "var(--font-mono)",
        fontSize: 12.5,
        color: "var(--ink)",
        border: "1px solid var(--border)",
      }}
    >
      {JSON.stringify(args ?? {}, null, 2)}
    </pre>
  )
}

/** Default Result renderer — single block of monospace text.
 * Errors get split: short summary on top, full trace inside <details>. */
export function DefaultResult({ result, status }: ToolResultProps) {
  const errored = status === "error"
  const text = result || "—"
  if (errored) {
    const lines = text.split("\n").filter((l) => l.trim().length > 0)
    const summary = lines.length > 0 ? lines[lines.length - 1] : text
    const hasMore = lines.length > 1
    return (
      <div
        className="rounded-lg px-2.5 py-2"
        style={{
          background: "var(--red-soft)",
          fontFamily: "var(--font-mono)",
          fontSize: 12.5,
          color: "var(--red)",
          border: "1px solid var(--red)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        <div style={{ fontWeight: 500 }}>{summary}</div>
        {hasMore && (
          <details className="mt-1.5">
            <summary
              className="cursor-pointer select-none"
              style={{ color: "var(--ink-3)", fontSize: 11.5 }}
            >
              show full trace
            </summary>
            <pre
              className="m-0 mt-1.5 break-words whitespace-pre-wrap"
              style={{ fontSize: 12, color: "var(--red)" }}
            >
              {text}
            </pre>
          </details>
        )}
      </div>
    )
  }
  return (
    <div
      className="rounded-lg px-2.5 py-2"
      style={{
        background: "var(--bg-soft)",
        fontFamily: "var(--font-mono)",
        fontSize: 12.5,
        color: "var(--ink-2)",
        border: "1px solid var(--border)",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {text}
    </div>
  )
}
