"use client"

import { Plus } from "lucide-react"
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

export function AddStepBar({ onAdd }: { onAdd: (kind: TaskStepKind) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {ADD_KINDS.map((k) => (
        <Button
          key={k}
          variant="outline"
          size="sm"
          onClick={() => onAdd(k)}
          className="h-7 text-[11px]"
        >
          <Plus className="h-3 w-3" />
          {KIND_LABEL[k]}
        </Button>
      ))}
    </div>
  )
}
