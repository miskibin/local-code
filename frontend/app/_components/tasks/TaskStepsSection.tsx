"use client"

import { ArrowDown, ArrowUp, Lock, Trash2 } from "lucide-react"
import { Fragment, useState } from "react"
import type { TaskStep, TaskStepKind } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { InsertSlot, KIND_COLOR, KIND_LABEL, makeStep } from "./StepsList"
import { StepEditor } from "./StepEditor"

const fieldChrome =
  "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink)] shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"

type Props = {
  steps: TaskStep[]
  onChange: (next: TaskStep[]) => void
}

function pinReportsLast(steps: TaskStep[]): TaskStep[] {
  const others = steps.filter((s) => s.kind !== "report")
  const reports = steps.filter((s) => s.kind === "report")
  return [...others, ...reports]
}

export function TaskStepsSection({ steps, onChange }: Props) {
  const emit = (next: TaskStep[]) => onChange(pinReportsLast(next))
  const [openSlot, setOpenSlot] = useState<number | null>(null)

  const firstReportIdx = steps.findIndex((s) => s.kind === "report")
  const reportsStart = firstReportIdx === -1 ? steps.length : firstReportIdx

  const move = (idx: number, delta: number) => {
    const next = [...steps]
    const target = idx + delta
    if (target < 0 || target >= next.length) return
    if (next[idx].kind === "report" || next[target].kind === "report") return
    ;[next[idx], next[target]] = [next[target], next[idx]]
    emit(next)
  }

  const remove = (idx: number) => {
    emit(steps.filter((_, i) => i !== idx))
  }

  const updateStep = (updated: TaskStep) => {
    emit(steps.map((s) => (s.id === updated.id ? updated : s)))
  }

  const insertAt = (idx: number, kind: TaskStepKind) => {
    const next = [...steps]
    next.splice(idx, 0, makeStep(kind, steps.length))
    emit(next)
    setOpenSlot(null)
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        className="flex items-center justify-between px-0.5"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: ".04em",
          color: "var(--ink-2)",
          textTransform: "uppercase",
        }}
      >
        <span>Steps {steps.length}</span>
      </div>

      <InsertSlot
        open={openSlot === 0}
        onOpen={() => setOpenSlot(0)}
        onClose={() => setOpenSlot(null)}
        onInsert={(k) => insertAt(0, k)}
      />

      {steps.map((step, i) => {
        const isReport = step.kind === "report"
        const canUp = !isReport && i > 0 && steps[i - 1].kind !== "report"
        const canDown =
          !isReport && i < reportsStart - 1 && i < steps.length - 1
        return (
          <Fragment key={step.id}>
          <div
            className="mx-auto w-full max-w-5xl rounded-lg p-4"
            style={{
              border: "1px solid var(--border-strong)",
              background: "var(--surface)",
              boxShadow:
                "0 1px 2px color-mix(in oklab, var(--ink) 5%, transparent)",
            }}
          >
            <div className="mb-3 flex min-w-0 items-center gap-2">
              <span
                className="shrink-0 rounded border px-1.5 py-0.5 font-medium tabular-nums"
                style={{
                  fontSize: 11,
                  background: "var(--bg-soft)",
                  borderColor: "var(--border-strong)",
                  color: "var(--ink-2)",
                  minWidth: 24,
                  textAlign: "center",
                }}
              >
                {i + 1}
              </span>
              <span
                className="shrink-0"
                style={{
                  fontSize: 10,
                  fontWeight: 500,
                  letterSpacing: ".04em",
                  color: KIND_COLOR[step.kind],
                }}
              >
                {KIND_LABEL[step.kind]}
              </span>
              {isReport && (
                <span
                  className="inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
                  style={{
                    background: "var(--hover)",
                    color: "var(--ink-2)",
                    border: "1px solid var(--border)",
                  }}
                  title="Report steps always run last"
                >
                  <Lock className="h-2.5 w-2.5" />
                  pinned to end
                </span>
              )}
              <Input
                value={step.title}
                onChange={(e) => updateStep({ ...step, title: e.target.value })}
                placeholder="Step title"
                className={cn(
                  fieldChrome,
                  "min-h-0 min-w-0 flex-1 border-transparent bg-transparent px-0 text-lg font-semibold text-[var(--ink)] shadow-none transition-colors placeholder:text-[var(--ink-3)] hover:bg-[var(--hover)]/50 focus-visible:border-[var(--border-strong)] focus-visible:bg-[var(--surface)] focus-visible:px-2 focus-visible:shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"
                )}
              />
              <div className="flex shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  title="Move up"
                  onClick={() => move(i, -1)}
                  disabled={!canUp}
                  className="rounded p-1.5 transition-colors hover:bg-[var(--hover-strong)] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                  style={{
                    background: "transparent",
                    border: 0,
                    color: "var(--ink-2)",
                  }}
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Move down"
                  onClick={() => move(i, 1)}
                  disabled={!canDown}
                  className="rounded p-1.5 transition-colors hover:bg-[var(--hover-strong)] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                  style={{
                    background: "transparent",
                    border: 0,
                    color: "var(--ink-2)",
                  }}
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Delete step"
                  onClick={() => remove(i)}
                  className="rounded p-1.5 transition-colors hover:bg-[var(--hover-strong)]"
                  style={{
                    background: "transparent",
                    border: 0,
                    color: "var(--ink-2)",
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <StepEditor step={step} onChange={updateStep} />
          </div>
          <InsertSlot
            open={openSlot === i + 1}
            onOpen={() => setOpenSlot(i + 1)}
            onClose={() => setOpenSlot(null)}
            onInsert={(k) => insertAt(i + 1, k)}
          />
          </Fragment>
        )
      })}

      {steps.length === 0 && (
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>
          No steps yet. Hover the line above to insert your first step.
        </p>
      )}
    </div>
  )
}
