"use client"

import { ArrowLeft, Braces, Loader2, Play } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { navigateToTaskRunUrl } from "@/lib/tasks"
import type { SavedTask, TaskRunVariables } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { MetadataPanel } from "./MetadataPanel"
import { RunVarsModal } from "./RunVarsModal"
import { TaskStepsSection } from "./TaskStepsSection"
import { VariablesPanel } from "./VariablesPanel"

const SAVE_DEBOUNCE_MS = 600

export function Builder({ taskId }: { taskId: string }) {
  const router = useRouter()
  const [task, setTask] = useState<SavedTask | null>(null)
  const [runOpen, setRunOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const dirtyRef = useRef(false)
  const savedSnapshotRef = useRef<string>("")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .getTask(taskId)
      .then((t) => {
        if (cancelled) return
        setTask(t)
        savedSnapshotRef.current = JSON.stringify(t)
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
      const saved = await api.updateTask(next.id, next)
      savedSnapshotRef.current = JSON.stringify(saved)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save task")
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
      const next = { ...prev, ...patch }
      dirtyRef.current = true
      return next
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
        className="flex h-dvh items-center justify-center"
        style={{ color: "var(--ink-3)" }}
      >
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading task…
      </div>
    )
  }

  if (!task) {
    return (
      <div
        className="flex h-dvh flex-col items-center justify-center gap-3"
        style={{ background: "var(--bg)" }}
      >
        <div style={{ color: "var(--ink-3)" }}>Task not found.</div>
        <Link href="/tasks">
          <Button variant="outline">Back to tasks</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="flex h-dvh flex-col" style={{ background: "var(--bg)" }}>
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
        </div>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <header
            className="sticky top-0 z-10 flex items-center gap-3 px-6 py-3"
            style={{ borderBottom: "1px solid var(--border)", background: "var(--bg)" }}
          >
            <Input
              value={task.title}
              onChange={(e) => updateTask({ title: e.target.value })}
              placeholder="Task title"
              style={{ fontSize: 16, fontWeight: 600, maxWidth: 480 }}
            />
            <div className="flex-1" />
            <span
              className="hidden text-xs sm:inline"
              style={{ color: "var(--ink-3)" }}
            >
              {saving ? "Saving…" : "Saved"}
            </span>
            <Button variant="outline" size="sm" onClick={copyTaskJson}>
              <Braces className="h-3.5 w-3.5" />
              Copy as JSON
            </Button>
            <Button onClick={() => setRunOpen(true)}>
              <Play className="h-3.5 w-3.5" /> Run task
            </Button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
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
