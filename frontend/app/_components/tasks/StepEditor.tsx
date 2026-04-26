"use client";

import type { TaskStep, TaskStepOutputKind } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  step: TaskStep;
  onChange: (step: TaskStep) => void;
};

const OUTPUT_KINDS: TaskStepOutputKind[] = [
  "text",
  "rows",
  "chart",
  "json",
  "file",
];

function ArgsEditor({
  value,
  onChange,
}: {
  value: Record<string, unknown> | null | undefined;
  onChange: (value: Record<string, unknown>) => void;
}) {
  const text =
    value === null || value === undefined
      ? "{}"
      : JSON.stringify(value, null, 2);
  return (
    <Textarea
      value={text}
      onChange={(e) => {
        try {
          const parsed = JSON.parse(e.target.value || "{}");
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            onChange(parsed as Record<string, unknown>);
          }
        } catch {
          /* leave; user is mid-edit */
        }
      }}
      style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}
      rows={8}
    />
  );
}

export function StepEditor({ step, onChange }: Props) {
  const update = (patch: Partial<TaskStep>) => onChange({ ...step, ...patch });

  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex items-baseline gap-2"
        style={{
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: ".04em",
          textTransform: "uppercase",
          color: "var(--accent)",
        }}
      >
        {step.kind}
      </div>
      <Input
        value={step.title}
        onChange={(e) => update({ title: e.target.value })}
        placeholder="Step title"
        style={{ fontWeight: 600, fontSize: 18 }}
      />

      {step.kind === "tool" && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <Label>Server</Label>
              <Input
                value={step.server ?? ""}
                onChange={(e) => update({ server: e.target.value })}
                placeholder="builtin or mcp server name"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label>Tool</Label>
              <Input
                value={step.tool ?? ""}
                onChange={(e) => update({ tool: e.target.value })}
                placeholder="tool name"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <Label>Arguments (JSON)</Label>
            <ArgsEditor
              value={step.args_template ?? {}}
              onChange={(v) => update({ args_template: v })}
            />
          </div>
        </>
      )}

      {step.kind === "code" && (
        <div className="flex flex-col gap-1">
          <Label>Python</Label>
          <Textarea
            value={step.code ?? ""}
            onChange={(e) => update({ code: e.target.value })}
            rows={12}
            placeholder="out({'rows': [...]})"
            style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}
          />
        </div>
      )}

      {step.kind === "subagent" && (
        <>
          <div className="flex flex-col gap-1">
            <Label>Subagent</Label>
            <Input
              value={step.subagent ?? ""}
              onChange={(e) => update({ subagent: e.target.value })}
              placeholder="research-agent | sql-agent"
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label>Prompt template</Label>
            <Textarea
              value={step.prompt ?? ""}
              onChange={(e) => update({ prompt: e.target.value })}
              rows={8}
              placeholder="Brief the subagent. Reference {{var.x}} and {{s1.rows}} as needed."
            />
          </div>
        </>
      )}

      {step.kind === "prompt" && (
        <div className="flex flex-col gap-1">
          <Label>Prompt template</Label>
          <Textarea
            value={step.prompt ?? ""}
            onChange={(e) => update({ prompt: e.target.value })}
            rows={10}
            placeholder="Free-form LLM call."
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-1">
          <Label>Output name</Label>
          <Input
            value={step.output_name}
            onChange={(e) =>
              update({
                output_name: e.target.value.replace(/[^a-zA-Z0-9_]/g, "_"),
              })
            }
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label>Output kind</Label>
          <select
            value={step.output_kind}
            onChange={(e) =>
              update({ output_kind: e.target.value as TaskStepOutputKind })
            }
            className="h-9 rounded-md px-2 text-sm"
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--ink)",
            }}
          >
            {OUTPUT_KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
