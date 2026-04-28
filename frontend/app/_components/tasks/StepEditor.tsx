"use client"

import { useEffect, useState } from "react"
import { AlertTriangle } from "lucide-react"
import { api } from "@/lib/api"
import type { TaskStep, TaskStepOutputKind, Tool } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { MessageResponse } from "@/components/ai-elements/message"
import { SchemaArgsEditor } from "./SchemaArgsEditor"
import { ToolPicker } from "./ToolPicker"

type Props = {
  step: TaskStep
  onChange: (step: TaskStep) => void
}

const OUTPUT_KINDS: TaskStepOutputKind[] = [
  "text",
  "rows",
  "chart",
  "json",
  "file",
]

const fieldChrome =
  "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink)] shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"

const labelMuted = "text-xs font-medium text-[var(--ink-2)]"

export function StepEditor({ step, onChange }: Props) {
  const [tools, setTools] = useState<Tool[] | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listTools()
      .then((res) => {
        if (!cancelled) setTools(res)
      })
      .catch(() => {
        if (!cancelled) setTools([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const update = (patch: Partial<TaskStep>) => onChange({ ...step, ...patch })

  const pickedTool =
    step.tool && tools
      ? (tools.find((t) => t.name === step.tool) ?? null)
      : null
  const isUnknownTool =
    step.kind === "tool" && !!step.tool && tools !== null && pickedTool === null

  return (
    <div className="flex flex-col gap-4">
      <Input
        value={step.title}
        onChange={(e) => update({ title: e.target.value })}
        placeholder="Step title"
        className={cn(
          fieldChrome,
          "border-transparent bg-transparent px-0 text-lg font-semibold text-[var(--ink)] shadow-none transition-colors placeholder:text-[var(--ink-3)] hover:bg-[var(--hover)]/50 focus-visible:border-[var(--border-strong)] focus-visible:bg-[var(--surface)] focus-visible:px-2 focus-visible:shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"
        )}
      />

      {step.kind === "tool" && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <Label className={cn(labelMuted, "tracking-wider uppercase")}>
              Tool
            </Label>
            <ToolPicker
              tools={tools ?? []}
              value={step.tool ?? ""}
              onPick={(t) => update({ tool: t?.name ?? "" })}
            />
            {isUnknownTool && (
              <div
                className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs"
                style={{
                  background: "var(--hover)",
                  color: "var(--ink)",
                  border: "1px solid var(--border-strong)",
                }}
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                Tool not found: <code>{step.tool}</code>
              </div>
            )}
          </div>

          {pickedTool || isUnknownTool ? (
            <SchemaArgsEditor
              schema={pickedTool?.args_schema ?? null}
              value={step.args_template ?? {}}
              onChange={(v) => update({ args_template: v })}
            />
          ) : (
            <div className="text-xs text-[var(--ink-2)]">
              Pick a tool above to edit its arguments.
            </div>
          )}
        </div>
      )}

      {step.kind === "code" && (
        <div className="flex flex-col gap-1">
          <Label className={labelMuted}>Python</Label>
          <Textarea
            value={step.code ?? ""}
            onChange={(e) => update({ code: e.target.value })}
            rows={12}
            placeholder="out({'rows': [...]})"
            className={cn(fieldChrome, "font-mono text-xs")}
          />
        </div>
      )}

      {step.kind === "subagent" && (
        <>
          <div className="flex flex-col gap-1">
            <Label className={labelMuted}>Subagent</Label>
            <Input
              className={fieldChrome}
              value={step.subagent ?? ""}
              onChange={(e) => update({ subagent: e.target.value })}
              placeholder="research-agent | sql-agent"
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label className={labelMuted}>Prompt template</Label>
            <Textarea
              value={step.prompt ?? ""}
              onChange={(e) => update({ prompt: e.target.value })}
              rows={8}
              placeholder="Brief the subagent. Reference {{var.x}} and {{s1.rows}} as needed."
              className={fieldChrome}
            />
          </div>
        </>
      )}

      {step.kind === "prompt" && (
        <div className="flex flex-col gap-1">
          <Label className={labelMuted}>Prompt template</Label>
          <Textarea
            value={step.prompt ?? ""}
            onChange={(e) => update({ prompt: e.target.value })}
            rows={10}
            placeholder="Free-form LLM call."
            className={fieldChrome}
          />
        </div>
      )}

      {step.kind === "report" && (
        <ReportEditor
          value={step.prompt ?? ""}
          onChange={(prompt) => update({ prompt })}
        />
      )}

      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-1">
          <Label className={labelMuted}>Output name</Label>
          <Input
            className={fieldChrome}
            value={step.output_name}
            onChange={(e) =>
              update({
                output_name: e.target.value.replace(/[^a-zA-Z0-9_]/g, "_"),
              })
            }
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label className={labelMuted}>Output kind</Label>
          {step.kind === "tool" ? (
            <div
              className="flex h-9 items-center rounded-md border px-3 text-sm font-medium"
              style={{
                borderColor: "var(--border-strong)",
                background: "var(--surface)",
                color: "var(--ink)",
                boxShadow:
                  "inset 0 1px 0 color-mix(in oklab, var(--ink) 5%, transparent)",
              }}
            >
              {step.output_kind}
            </div>
          ) : (
            <Select
              value={step.output_kind}
              onValueChange={(v) =>
                update({ output_kind: v as TaskStepOutputKind })
              }
            >
              <SelectTrigger className={cn("w-full", fieldChrome)}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OUTPUT_KINDS.map((k) => (
                  <SelectItem key={k} value={k}>
                    {k}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportEditor({
  value,
  onChange,
}: {
  value: string
  onChange: (next: string) => void
}) {
  const [mode, setMode] = useState<"edit" | "preview">("edit")
  const empty = !value.trim()
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Label className={cn(labelMuted, "tracking-wider uppercase")}>
          Report markdown
        </Label>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setMode("edit")}
            className={cn(
              "rounded px-2 py-0.5 text-[11px] font-medium transition-colors",
              mode === "edit"
                ? "bg-[var(--hover-strong)] text-[var(--ink)]"
                : "text-[var(--ink-2)] hover:bg-[var(--hover)]"
            )}
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => setMode("preview")}
            className={cn(
              "rounded px-2 py-0.5 text-[11px] font-medium transition-colors",
              mode === "preview"
                ? "bg-[var(--hover-strong)] text-[var(--ink)]"
                : "text-[var(--ink-2)] hover:bg-[var(--hover)]"
            )}
          >
            Preview
          </button>
        </div>
      </div>
      {mode === "edit" ? (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={12}
          placeholder="## Results&#10;&#10;Reference outputs with {{s1.artifact_id}} or {{var.x}}."
          className={cn(fieldChrome, "font-mono text-xs")}
        />
      ) : empty ? (
        <div
          className="rounded-md border px-3 py-6 text-center text-xs"
          style={{
            borderColor: "var(--border-strong)",
            background: "var(--bg-soft)",
            color: "var(--ink-2)",
          }}
        >
          Empty report. Switch to Edit and write markdown.
        </div>
      ) : (
        <div
          className="rounded-md border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--border-strong)",
            background: "var(--surface)",
            color: "var(--ink)",
          }}
        >
          <MessageResponse>{value}</MessageResponse>
        </div>
      )}
      <span className="text-[11px] text-[var(--ink-2)]">
        Rendered as markdown into the chat. <code>{"{{s1.artifact_id}}"}</code>{" "}
        and <code>{"{{var.x}}"}</code> templates resolve at run time.
      </span>
    </div>
  )
}
