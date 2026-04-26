"use client";

import type { ToolArgsProps, ToolResultProps } from "./types";

/** Default Args renderer — pretty-printed JSON in a monospace block. */
export function DefaultArgs({ args }: ToolArgsProps) {
  return (
    <pre
      className="m-0 whitespace-pre-wrap break-words rounded-lg px-2.5 py-2"
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
  );
}

/** Default Result renderer — single block of monospace text. */
export function DefaultResult({ result, status }: ToolResultProps) {
  const errored = status === "error";
  return (
    <div
      className="rounded-lg px-2.5 py-2"
      style={{
        background: errored ? "var(--red-soft)" : "var(--bg-soft)",
        fontFamily: "var(--font-mono)",
        fontSize: 12.5,
        color: errored ? "var(--red)" : "var(--ink-2)",
        border: `1px solid ${errored ? "var(--red)" : "var(--border)"}`,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {result || "—"}
    </div>
  );
}
