"use client"

import type { SavedTask } from "@/lib/types"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

type Props = {
  task: SavedTask
  onChange: (patch: Partial<SavedTask>) => void
}

export function MetadataPanel({ task, onChange }: Props) {
  const tagsText = (task.tags ?? []).join(", ")
  return (
    <div
      className="flex flex-col gap-2 rounded-md p-2.5"
      style={{ border: "1px solid var(--border)" }}
    >
      <div
        className="flex items-center justify-between px-1 text-[11px] font-medium tracking-wider uppercase"
        style={{ color: "var(--ink-3)" }}
      >
        <span>Metadata</span>
        {task.creator && (
          <span style={{ color: "var(--ink-3)", textTransform: "none" }}>
            by {task.creator}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <Label className="text-[11px]" style={{ color: "var(--ink-3)" }}>
          Role
        </Label>
        <Input
          value={task.role ?? ""}
          onChange={(e) => onChange({ role: e.target.value || null })}
          placeholder="analyst, ops, anyone…"
          className="h-8 text-[13px]"
        />
      </div>

      <div className="flex flex-col gap-1">
        <Label className="text-[11px]" style={{ color: "var(--ink-3)" }}>
          Tags
        </Label>
        <Input
          value={tagsText}
          onChange={(e) =>
            onChange({
              tags: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
          placeholder="comma, separated"
          className="h-8 text-[13px]"
        />
      </div>
    </div>
  )
}
