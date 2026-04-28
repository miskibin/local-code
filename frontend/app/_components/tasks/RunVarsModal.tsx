"use client"

import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import type { SavedTask, TaskRunVariables } from "@/lib/types"

type Props = {
  task: SavedTask | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onRun: (vars: TaskRunVariables) => void
}

function defaultsFor(task: SavedTask | null): TaskRunVariables {
  const out: TaskRunVariables = {}
  if (!task) return out
  for (const v of task.variables) {
    if (v.type === "boolean") {
      out[v.name] = Boolean(v.default ?? false)
    } else if (v.type === "number") {
      const n = Number(v.default)
      out[v.name] = Number.isFinite(n) ? n : 0
    } else {
      out[v.name] = String(v.default ?? "")
    }
  }
  return out
}

export function RunVarsModal({ task, open, onOpenChange, onRun }: Props) {
  const [values, setValues] = useState<TaskRunVariables>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setValues(defaultsFor(task))
      setError(null)
    }
  }, [open, task])

  if (!task) return null

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    for (const v of task.variables) {
      if (!v.required) continue
      const cur = values[v.name]
      const empty =
        cur === undefined ||
        cur === null ||
        (typeof cur === "string" && cur.trim() === "")
      if (empty) {
        setError(`Variable "${v.name}" is required`)
        return
      }
    }
    onRun(values)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run task</DialogTitle>
          <DialogDescription>{task.title}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4">
          {task.variables.length === 0 && (
            <div style={{ color: "var(--ink-3)", fontSize: 13 }}>
              No variables — task runs with built-in values.
            </div>
          )}
          {task.variables.map((v) => (
            <div key={v.name} className="flex flex-col gap-1.5">
              <Label htmlFor={`var-${v.name}`}>
                {v.name}
                {v.required && (
                  <span style={{ color: "var(--accent)" }}> *</span>
                )}
              </Label>
              {v.type === "boolean" ? (
                <Switch
                  id={`var-${v.name}`}
                  checked={Boolean(values[v.name])}
                  onCheckedChange={(checked) =>
                    setValues((p) => ({ ...p, [v.name]: checked }))
                  }
                />
              ) : (
                <Input
                  id={`var-${v.name}`}
                  type={v.type === "number" ? "number" : "text"}
                  value={String(values[v.name] ?? "")}
                  onChange={(e) =>
                    setValues((p) => ({
                      ...p,
                      [v.name]:
                        v.type === "number"
                          ? Number(e.target.value)
                          : e.target.value,
                    }))
                  }
                />
              )}
              <span style={{ color: "var(--ink-4)", fontSize: 11 }}>
                {`{{${v.name}}}`} · {v.type}
              </span>
            </div>
          ))}
          {error && (
            <div style={{ color: "var(--accent)", fontSize: 13 }}>{error}</div>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit">Run task</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
