"use client"

import { useEffect, useState } from "react"
import { Check, Copy } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import type { TaskStep, Tool } from "@/lib/types"

type Row = { ref: string; desc: string }

const ARTIFACT_KINDS = new Set(["rows", "chart", "file", "json"])

function sourceLabel(step: TaskStep, tool?: Tool): string {
  if (step.kind === "tool") return tool?.name || step.tool || "tool"
  if (step.kind === "code") return "Python code"
  if (step.kind === "subagent")
    return step.subagent ? `${step.subagent} subagent` : "subagent"
  return step.kind
}

function buildRows(step: TaskStep, tool?: Tool): Row[] {
  const src = sourceLabel(step, tool)
  const tail = tool?.description ? ` — ${tool.description}` : ""
  const rows: Row[] = [
    { ref: `{{${step.id}.${step.output_name}}}`, desc: `${src}${tail}` },
  ]
  const hasArtifact =
    step.kind !== "prompt" || ARTIFACT_KINDS.has(step.output_kind)
  if (hasArtifact) {
    rows.push({ ref: `{{${step.id}.artifact_id}}`, desc: `artifact id · ${src}` })
  }
  return rows
}

export function StepOutputsPanel({ steps }: { steps: TaskStep[] }) {
  const [tools, setTools] = useState<Tool[]>([])

  useEffect(() => {
    let cancelled = false
    api.listTools().then(
      (r) => !cancelled && setTools(r),
      () => !cancelled && setTools([])
    )
    return () => {
      cancelled = true
    }
  }, [])

  const usable = steps.filter((s) => s.kind !== "report")
  const rows = usable.flatMap((s) =>
    buildRows(
      s,
      tools.find((t) => t.name === s.tool)
    )
  )

  return (
    <div className="flex flex-col gap-1">
      <div
        className="px-1 text-[11px] font-medium tracking-wider uppercase"
        style={{ color: "var(--ink-3)" }}
      >
        Step outputs {rows.length}
      </div>
      {usable.length === 0 ? (
        <div
          className="rounded-md px-2.5 py-2 text-[11px]"
          style={{ border: "1px dashed var(--border)", color: "var(--ink-3)" }}
        >
          Add a step to expose references.
        </div>
      ) : (
        rows.map((r) => <RefRow key={r.ref} row={r} />)
      )}
    </div>
  )
}

function RefRow({ row }: { row: Row }) {
  const [copied, setCopied] = useState(false)
  const onCopy = () =>
    void navigator.clipboard.writeText(row.ref).then(
      () => {
        setCopied(true)
        toast.success("Reference copied")
        window.setTimeout(() => setCopied(false), 1200)
      },
      () => toast.error("Could not copy")
    )
  return (
    <button
      type="button"
      onClick={onCopy}
      title={row.ref}
      className="group flex items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-[var(--hover)]"
    >
      <code
        className="shrink-0 truncate rounded px-1.5 py-0.5 text-xs"
        style={{ background: "var(--hover)", color: "var(--accent)" }}
      >
        {row.ref}
      </code>
      <span
        className="line-clamp-1 flex-1 text-[11px]"
        style={{ color: "var(--ink-3)" }}
      >
        {row.desc}
      </span>
      {copied ? (
        <Check className="h-3 w-3 shrink-0" style={{ color: "var(--accent)" }} />
      ) : (
        <Copy
          className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-100"
          style={{ color: "var(--ink-3)" }}
        />
      )}
    </button>
  )
}
