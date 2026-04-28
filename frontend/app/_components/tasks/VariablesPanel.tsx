"use client"

import { Plus, X } from "lucide-react"
import type { TaskVariable, TaskVariableType } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type Props = {
  variables: TaskVariable[]
  onChange: (next: TaskVariable[]) => void
}

const EMPTY_VAR: TaskVariable = {
  name: "",
  type: "string",
  default: "",
  required: true,
}

const TYPES: TaskVariableType[] = ["string", "number", "boolean"]

export function VariablesPanel({ variables, onChange }: Props) {
  const update = (idx: number, patch: Partial<TaskVariable>) =>
    onChange(variables.map((v, i) => (i === idx ? { ...v, ...patch } : v)))

  const remove = (idx: number) =>
    onChange(variables.filter((_, i) => i !== idx))

  const add = () =>
    onChange([
      ...variables,
      { ...EMPTY_VAR, name: `var${variables.length + 1}` },
    ])

  return (
    <div className="flex flex-col gap-2">
      <div
        className="flex items-center justify-between px-1 text-[11px] font-medium tracking-wider uppercase"
        style={{ color: "var(--ink-3)" }}
      >
        <span>Variables {variables.length}</span>
      </div>
      {variables.map((v, i) => (
        <div
          key={i}
          className="flex flex-col gap-1.5 rounded-md p-2.5"
          style={{ border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between gap-2">
            <code
              className="truncate rounded px-1.5 py-0.5 text-xs"
              style={{
                background: "var(--hover)",
                color: "var(--accent)",
              }}
            >
              {`{{${v.name || "name"}}}`}
            </code>
            <div className="flex items-center gap-1">
              <Select
                value={v.type}
                onValueChange={(value) =>
                  update(i, { type: value as TaskVariableType })
                }
              >
                <SelectTrigger
                  size="sm"
                  className="h-7 text-[11px]"
                  style={{ color: "var(--ink-2)" }}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => remove(i)}
                aria-label="Remove variable"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          <Input
            placeholder="name"
            value={v.name}
            onChange={(e) =>
              update(i, { name: e.target.value.replace(/[^a-zA-Z0-9_]/g, "_") })
            }
            className="text-[13px]"
          />
          <Input
            placeholder="Default value"
            value={String(v.default ?? "")}
            onChange={(e) => update(i, { default: e.target.value })}
            className="text-[13px]"
          />
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} className="justify-start">
        <Plus className="h-3.5 w-3.5" /> Add variable
      </Button>
    </div>
  )
}
