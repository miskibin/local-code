"use client"

import { Plus, X } from "lucide-react"
import { nanoid } from "nanoid"
import type { TaskStep, TaskStepKind } from "@/lib/types"
import { Button } from "@/components/ui/button"

export const KIND_LABEL: Record<TaskStepKind, string> = {
  tool: "TOOL",
  code: "CODE",
  subagent: "SUBAGENT",
  prompt: "PROMPT",
  report: "REPORT",
}

export const KIND_COLOR: Record<TaskStepKind, string> = {
  tool: "var(--accent)",
  code: "#9333ea",
  subagent: "#0ea5e9",
  prompt: "#10b981",
  report: "#f59e0b",
}

const ADD_KINDS: TaskStepKind[] = [
  "tool",
  "code",
  "subagent",
  "prompt",
  "report",
]

export function makeStep(kind: TaskStepKind, index: number): TaskStep {
  const id = `s${index + 1}_${nanoid(4)}`
  const wantsPrompt =
    kind === "subagent" || kind === "prompt" || kind === "report"
  return {
    id,
    kind,
    title: kind === "report" ? "Results" : `Step ${index + 1}`,
    tool: kind === "tool" ? "" : null,
    args_template: kind === "tool" ? {} : null,
    code: kind === "code" ? "" : null,
    subagent: kind === "subagent" ? "" : null,
    prompt: wantsPrompt ? (kind === "report" ? "## Results\n\n" : "") : null,
    output_name: kind === "report" ? "report" : "output",
    output_kind: "text",
  }
}

/**
 * Thin insertion zone shown between steps. Collapsed: a hover-only hairline
 * with a centered + chip. Expanded: inline kind picker.
 */
export function InsertSlot({
  open,
  onOpen,
  onClose,
  onInsert,
}: {
  open: boolean
  onOpen: () => void
  onClose: () => void
  onInsert: (k: TaskStepKind) => void
}) {
  if (!open) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-label="Insert step here"
        className="group relative flex h-5 w-full cursor-pointer items-center justify-center"
        style={{ background: "transparent", border: 0, padding: 0 }}
      >
        <span
          className="h-px w-full transition-colors group-hover:bg-[var(--border-strong)]"
          style={{ background: "transparent" }}
        />
        <span
          className="absolute inline-flex items-center gap-1 rounded-full px-2 py-0.5 opacity-0 transition-opacity group-hover:opacity-100"
          style={{
            background: "var(--bg)",
            border: "1px solid var(--border-strong)",
            fontSize: 10.5,
            color: "var(--ink-2)",
            letterSpacing: ".04em",
            textTransform: "uppercase",
            fontWeight: 500,
          }}
        >
          <Plus className="h-3 w-3" />
          Insert
        </span>
      </button>
    )
  }
  return (
    <div
      className="flex flex-wrap items-center justify-center gap-1.5 py-1"
      role="group"
      aria-label="Insert step"
    >
      {ADD_KINDS.map((k) => (
        <Button
          key={k}
          variant="outline"
          size="sm"
          onClick={() => onInsert(k)}
          className="h-7 text-[11px]"
        >
          <Plus className="h-3 w-3" />
          {KIND_LABEL[k]}
        </Button>
      ))}
      <button
        type="button"
        onClick={onClose}
        aria-label="Cancel insert"
        className="ml-1 rounded p-1 transition-colors hover:bg-[var(--hover-strong)]"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-3)",
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  )
}
