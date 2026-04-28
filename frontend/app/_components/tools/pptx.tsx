"use client"

import { Download, FileText } from "lucide-react"
import { BACKEND_URL } from "@/lib/api"
import type { ToolRenderer, ToolResultProps } from "./types"
import { DefaultResult } from "./default"

const ART_ID_RE = /\bart_[A-Za-z0-9]+/

function extractArtifactId(text: string): string | null {
  const m = text.match(ART_ID_RE)
  return m ? m[0] : null
}

function PptxResult({ result, status, step }: ToolResultProps) {
  if (status === "error" || !result) {
    return <DefaultResult result={result} status={status} step={step} />
  }
  const aid = extractArtifactId(result)
  if (!aid) {
    return <DefaultResult result={result} status={status} step={step} />
  }
  const args =
    (step.args as { deck?: { title?: string; slides?: unknown[] } } | undefined) ?? {}
  const title = args.deck?.title ?? "Presentation"
  const slideCount = Array.isArray(args.deck?.slides) ? args.deck.slides.length : null
  const href = `${BACKEND_URL}/artifacts/${aid}/file`

  return (
    <div className="flex flex-col gap-2">
      <div
        className="flex items-center gap-3 rounded-lg px-3 py-2.5"
        style={{
          background: "var(--bg-soft)",
          border: "1px solid var(--border)",
        }}
      >
        <FileText size={20} style={{ color: "var(--accent)" }} />
        <div className="flex min-w-0 flex-1 flex-col">
          <span
            className="truncate text-sm font-medium"
            style={{ color: "var(--ink)" }}
          >
            {title}
          </span>
          <span className="text-xs" style={{ color: "var(--ink-2)" }}>
            {slideCount !== null ? `${slideCount} slides · ` : ""}.pptx
          </span>
        </div>
        <a
          href={href}
          download
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium"
          style={{
            background: "var(--accent)",
            color: "var(--accent-ink)",
            border: "1px solid var(--accent)",
          }}
        >
          <Download size={14} />
          Download
        </a>
      </div>
    </div>
  )
}

export const pptxRenderer: ToolRenderer = {
  Result: PptxResult,
}
