"use client"

import { TASK_ROLES, type TaskRoleId } from "@/lib/roles"
import type { SavedTask } from "@/lib/types"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const UNASSIGNED = "__unassigned__"

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
        <Select
          value={task.role ?? UNASSIGNED}
          onValueChange={(value) =>
            onChange({
              role: value === UNASSIGNED ? null : (value as TaskRoleId),
            })
          }
        >
          <SelectTrigger className="h-8 w-full text-[13px]">
            <SelectValue placeholder="Unassigned" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
            {TASK_ROLES.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
