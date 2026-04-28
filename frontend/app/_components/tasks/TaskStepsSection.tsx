"use client"

import { ArrowDown, ArrowUp, Lock, Trash2 } from "lucide-react"
import type { TaskStep, TaskStepKind } from "@/lib/types"
import { AddStepBar, KIND_COLOR, KIND_LABEL, makeStep } from "./StepsList"
import { StepEditor } from "./StepEditor"

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

  return (
    <div className="flex flex-col gap-6">
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

      {steps.map((step, i) => {
        const isReport = step.kind === "report"
        const canUp = !isReport && i > 0 && steps[i - 1].kind !== "report"
        const canDown =
          !isReport && i < reportsStart - 1 && i < steps.length - 1
        return (
          <div
            key={step.id}
            className="rounded-lg p-4"
            style={{
              border: "1px solid var(--border-strong)",
              background: "var(--surface)",
              boxShadow:
                "0 1px 2px color-mix(in oklab, var(--ink) 5%, transparent)",
            }}
          >
            <div className="mb-3 flex items-center gap-2">
              <span
                className="rounded border px-1.5 py-0.5 font-medium tabular-nums"
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
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
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
              <div className="flex-1" />
              <div className="flex items-center gap-0.5">
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
        )
      })}

      {steps.length === 0 && (
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>
          No steps yet. Add a tool, code, subagent, or prompt step below.
        </p>
      )}

      <AddStepBar
        onAdd={(kind: TaskStepKind) =>
          emit([...steps, makeStep(kind, steps.length)])
        }
      />
    </div>
  )
}
