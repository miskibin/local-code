"use client"

import { Streamdown } from "streamdown"

import type { ArtifactSourceKind } from "@/lib/types"

const LANG_BY_KIND: Record<ArtifactSourceKind, string> = {
  python: "python",
  sql: "sql",
  text: "text",
}

export function ArtifactSourceCode({
  sourceKind,
  sourceCode,
}: {
  sourceKind: ArtifactSourceKind | null | undefined
  sourceCode: string | null | undefined
}) {
  if (!sourceCode) return null
  const lang = LANG_BY_KIND[sourceKind ?? "text"] ?? "text"
  const fenced = `\`\`\`${lang}\n${sourceCode}\n\`\`\``
  return (
    <details
      className="mt-3 rounded-lg"
      style={{ border: "1px solid var(--border)" }}
    >
      <summary
        className="cursor-pointer px-3 py-2 text-[12px] font-medium select-none"
        style={{ color: "var(--ink-2)" }}
      >
        Source code{sourceKind ? ` · ${sourceKind}` : ""}
      </summary>
      <div className="px-3 pb-3" style={{ fontSize: 12.5 }}>
        <Streamdown>{fenced}</Streamdown>
      </div>
    </details>
  )
}
