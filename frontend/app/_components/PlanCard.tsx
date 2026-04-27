"use client"

import { Circle, CircleCheck, Loader2 } from "lucide-react"
import {
  Plan,
  PlanAction,
  PlanContent,
  PlanDescription,
  PlanHeader,
  PlanTitle,
  PlanTrigger,
} from "@/components/ai-elements/plan"
import type { Todo } from "@/lib/types"

function progressLabel(todos: Todo[]): string {
  const total = todos.length
  const done = todos.filter((t) => t.status === "completed").length
  if (done === total) return `All done · ${done}/${total}`
  return `In progress · ${done}/${total}`
}

function StatusIcon({ status }: { status: Todo["status"] }) {
  if (status === "completed") {
    return (
      <CircleCheck
        className="h-4 w-4 shrink-0"
        style={{ color: "var(--accent-ink)" }}
      />
    )
  }
  if (status === "in_progress") {
    return (
      <Loader2
        className="lc-spin h-4 w-4 shrink-0"
        style={{ color: "var(--accent)" }}
      />
    )
  }
  return (
    <Circle className="h-4 w-4 shrink-0" style={{ color: "var(--ink-3)" }} />
  )
}

function TodoRow({ todo }: { todo: Todo }) {
  const completed = todo.status === "completed"
  return (
    <li
      className="flex items-start gap-2.5 py-1.5 text-[14px]"
      style={{ color: completed ? "var(--ink-3)" : "var(--ink)" }}
    >
      <span className="mt-0.5">
        <StatusIcon status={todo.status} />
      </span>
      <span
        className="flex-1 leading-snug"
        style={{
          textDecoration: completed ? "line-through" : "none",
        }}
      >
        {todo.content}
      </span>
    </li>
  )
}

export function PlanCard({
  todos,
  streaming,
}: {
  todos: Todo[]
  streaming: boolean
}) {
  if (todos.length === 0) return null
  return (
    <div className="lc-reveal my-1.5 mb-3.5">
      <Plan
        defaultOpen
        isStreaming={streaming}
        style={{
          background: "var(--tool-bg)",
          border: "1px solid var(--tool-border)",
        }}
      >
        <PlanHeader className="flex flex-row items-center justify-between gap-3 px-3.5 py-2.5">
          <div className="flex flex-col gap-0.5">
            <PlanTitle className="text-[14px]">Plan</PlanTitle>
            <PlanDescription
              className="text-[12px]"
              style={{ color: "var(--ink-3)" }}
            >
              {progressLabel(todos)}
            </PlanDescription>
          </div>
          <PlanAction className="self-center">
            <PlanTrigger />
          </PlanAction>
        </PlanHeader>
        <PlanContent
          className="px-3.5 pt-0 pb-3"
          style={{
            borderTop: "1px solid var(--tool-border)",
            background: "var(--surface)",
          }}
        >
          <ol className="m-0 list-none p-0 pt-2">
            {todos.map((t, i) => (
              <TodoRow key={i} todo={t} />
            ))}
          </ol>
        </PlanContent>
      </Plan>
    </div>
  )
}
