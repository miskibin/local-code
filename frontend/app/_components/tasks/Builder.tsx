"use client"

import {
  AlertTriangle,
  ArrowLeft,
  Braces,
  Loader2,
  Play,
  Undo2,
} from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api, TaskValidationError } from "@/lib/api"
import { navigateToTaskRunUrl } from "@/lib/tasks"
import type { SavedTask, TaskRunVariables, ValidationIssue } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { MetadataPanel } from "./MetadataPanel"
import { RunVarsModal } from "./RunVarsModal"
import { StepOutputsPanel } from "./StepOutputsPanel"
import { TaskStepsSection } from "./TaskStepsSection"
import { VariablesPanel } from "./VariablesPanel"

const SAVE_DEBOUNCE_MS = 600

export function Builder({ taskId }: { taskId: string }) {
  const router = useRouter()
  const [task, setTask] = useState<SavedTask | null>(null)
  const [runOpen, setRunOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [issues, setIssues] = useState<ValidationIssue[]>([])
  const [canUndo, setCanUndo] = useState(false)
  const dirtyRef = useRef(false)
  const savedSnapshotRef = useRef<string>("")
  const historyRef = useRef<SavedTask[]>([])
  const HISTORY_MAX = 50

  const hasErrors = issues.some((i) => i.severity === "error")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .getTask(taskId)
      .then(async (t) => {
        if (cancelled) return
        setTask(t)
        savedSnapshotRef.current = JSON.stringify(t)
        try {
          const found = await api.validateTask(t)
          if (!cancelled) setIssues(found)
        } catch {
          // Validation lookup is advisory; ignore failures.
        }
      })
      .catch((e) => {
        if (cancelled) return
        toast.error(e instanceof Error ? e.message : "Failed to load task")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [taskId])

  const persist = useCallback(async (next: SavedTask) => {
    const snap = JSON.stringify(next)
    if (snap === savedSnapshotRef.current) return
    setSaving(true)
    try {
      // Validate first; skip the write entirely when errors exist so we
      // don't spam 422s while the user is mid-fix.
      const found = await api.validateTask(next)
      setIssues(found)
      if (found.some((i) => i.severity === "error")) return
      const saved = await api.updateTask(next.id, next)
      savedSnapshotRef.current = JSON.stringify(saved)
    } catch (e) {
      if (e instanceof TaskValidationError) {
        setIssues(e.issues)
      } else {
        toast.error(e instanceof Error ? e.message : "Failed to save task")
      }
    } finally {
      setSaving(false)
    }
  }, [])

  useEffect(() => {
    if (!task) return
    if (!dirtyRef.current) return
    const handle = setTimeout(() => {
      void persist(task)
      dirtyRef.current = false
    }, SAVE_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [task, persist])

  const updateTask = (patch: Partial<SavedTask>) => {
    setTask((prev) => {
      if (!prev) return prev
      historyRef.current = [...historyRef.current, prev].slice(-HISTORY_MAX)
      setCanUndo(true)
      dirtyRef.current = true
      return { ...prev, ...patch }
    })
  }

  const onUndo = () => {
    setTask((prev) => {
      if (!prev) return prev
      const stack = historyRef.current
      if (stack.length === 0) return prev
      const last = stack[stack.length - 1]
      historyRef.current = stack.slice(0, -1)
      setCanUndo(historyRef.current.length > 0)
      dirtyRef.current = true
      return last
    })
  }

  const copyTaskJson = () => {
    if (!task) return
    const text = JSON.stringify(task, null, 2)
    void navigator.clipboard.writeText(text).then(
      () => toast.success("Task copied as JSON"),
      () => toast.error("Could not copy to clipboard")
    )
  }

  const onRun = (vars: TaskRunVariables) => {
    if (!task) return
    setRunOpen(false)
    navigateToTaskRunUrl(router, task.id, vars)
  }

  if (loading) {
    return (
      <div
        className={cn(
          "lc-login-bg relative flex h-dvh items-center justify-center"
        )}
        style={{ color: "var(--ink-3)" }}
      >
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading task…
      </div>
    )
  }

  if (!task) {
    return (
      <div
        className={cn(
          "lc-login-bg relative flex h-dvh flex-col items-center justify-center gap-3"
        )}
      >
        <div style={{ color: "var(--ink-3)" }}>Task not found.</div>
        <Link href="/tasks">
          <Button variant="outline">Back to tasks</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className={cn("lc-login-bg relative flex h-dvh flex-col")}>
      <div
        className="flex items-center gap-3 px-6 py-3"
        style={{ borderBottom: "1px solid var(--border)", minHeight: 52 }}
      >
        <Link
          href="/tasks"
          aria-label="Back to tasks"
          className="inline-flex items-center justify-center rounded-md p-1.5"
          style={{ color: "var(--ink-2)" }}
        >
          <ArrowLeft className="h-[17px] w-[17px]" />
        </Link>
        <div className="flex flex-1 items-center gap-2">
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              letterSpacing: ".04em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            Tasks
          </span>
          <span style={{ color: "var(--ink-4)", fontSize: 11 }}>·</span>
          <span style={{ fontSize: 13, color: "var(--ink-2)" }}>Builder</span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <div
          className="flex w-[400px] flex-shrink-0 flex-col gap-4 overflow-y-auto p-4"
          style={{
            background: "var(--bg-soft)",
            borderRight: "1px solid var(--border)",
          }}
        >
          <Textarea
            value={task.description}
            onChange={(e) => updateTask({ description: e.target.value })}
            rows={3}
            placeholder="Describe what this task does."
            style={{ fontSize: 13 }}
          />
          <MetadataPanel task={task} onChange={updateTask} />
          <VariablesPanel
            variables={task.variables}
            onChange={(variables) => updateTask({ variables })}
          />
          <StepOutputsPanel steps={task.steps} />
        </div>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <header
            className="sticky top-0 z-10 flex items-center gap-3 px-6 py-3"
            style={{
              borderBottom: "1px solid var(--border)",
              background: "var(--bg)",
            }}
          >
            <Button
              variant="outline"
              size="sm"
              onClick={onUndo}
              disabled={!canUndo}
              aria-label="Undo last change"
              title="Undo last change"
            >
              <Undo2 className="h-3.5 w-3.5" />
              Undo
            </Button>
            <Input
              value={task.title}
              onChange={(e) => updateTask({ title: e.target.value })}
              placeholder="Task title"
              style={{ fontSize: 16, fontWeight: 600, maxWidth: 480 }}
            />
            <div className="flex-1" />
            <span
              className="hidden text-xs sm:inline"
              style={{ color: hasErrors ? "var(--red)" : "var(--ink-3)" }}
            >
              {saving
                ? "Saving…"
                : hasErrors
                  ? `Save blocked: ${issues.filter((i) => i.severity === "error").length} issue(s)`
                  : "Saved"}
            </span>
            <Button variant="outline" size="sm" onClick={copyTaskJson}>
              <Braces className="h-3.5 w-3.5" />
              Copy as JSON
            </Button>
            <Button onClick={() => setRunOpen(true)} disabled={hasErrors}>
              <Play className="h-3.5 w-3.5" /> Run task
            </Button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            {issues.length > 0 && (
              <div
                className="mb-4 rounded-lg p-3"
                style={{
                  background: issues.some((i) => i.severity === "error")
                    ? "var(--red-soft)"
                    : "var(--bg-soft)",
                  border: `1px solid ${
                    issues.some((i) => i.severity === "error")
                      ? "var(--red)"
                      : "var(--amber)"
                  }`,
                  color: "var(--ink)",
                }}
              >
                <div
                  className="mb-1.5 inline-flex items-center gap-1.5"
                  style={{ fontWeight: 500, fontSize: 13 }}
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {(() => {
                    const errs = issues.filter(
                      (i) => i.severity === "error"
                    ).length
                    const warns = issues.filter(
                      (i) => i.severity === "warning"
                    ).length
                    const parts: string[] = []
                    if (errs > 0) parts.push(`${errs} error(s)`)
                    if (warns > 0) parts.push(`${warns} warning(s)`)
                    return parts.join(", ")
                  })()}
                </div>
                <ul
                  className="m-0 list-disc pl-5"
                  style={{ fontSize: 12.5, color: "var(--ink-2)" }}
                >
                  {issues.map((iss, idx) => (
                    <li key={idx}>
                      {iss.step_id && (
                        <code
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--ink-3)",
                            marginRight: 6,
                          }}
                        >
                          [{iss.step_id}
                          {iss.field ? `.${iss.field}` : ""}]
                        </code>
                      )}
                      {iss.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <TaskStepsSection
              steps={task.steps}
              onChange={(steps) => updateTask({ steps })}
            />
          </div>
        </div>
      </div>

      <RunVarsModal
        task={task}
        open={runOpen}
        onOpenChange={setRunOpen}
        onRun={onRun}
      />
    </div>
  )
}
