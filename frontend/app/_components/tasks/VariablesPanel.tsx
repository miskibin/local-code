"use client";

import { Plus, X } from "lucide-react";
import type { TaskVariable, TaskVariableType } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = {
  variables: TaskVariable[];
  onChange: (next: TaskVariable[]) => void;
};

const EMPTY_VAR: TaskVariable = {
  name: "",
  type: "string",
  label: "",
  default: "",
  required: true,
};

export function VariablesPanel({ variables, onChange }: Props) {
  const update = (idx: number, patch: Partial<TaskVariable>) =>
    onChange(variables.map((v, i) => (i === idx ? { ...v, ...patch } : v)));

  const remove = (idx: number) =>
    onChange(variables.filter((_, i) => i !== idx));

  const add = () =>
    onChange([
      ...variables,
      { ...EMPTY_VAR, name: `var${variables.length + 1}` },
    ]);

  return (
    <div className="flex flex-col gap-2">
      <div
        className="flex items-center justify-between px-1"
        style={{
          fontSize: 11,
          fontWeight: 500,
          letterSpacing: ".04em",
          color: "var(--ink-3)",
          textTransform: "uppercase",
        }}
      >
        <span>Variables {variables.length}</span>
      </div>
      {variables.map((v, i) => (
        <div
          key={i}
          className="flex flex-col gap-1.5 rounded-md p-2.5"
          style={{ border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between">
            <code
              className="rounded px-1.5 py-0.5"
              style={{
                background: "var(--hover)",
                fontSize: 12,
                color: "var(--accent)",
              }}
            >
              {`{{${v.name || "name"}}}`}
            </code>
            <div className="flex items-center gap-1">
              <select
                value={v.type}
                onChange={(e) =>
                  update(i, { type: e.target.value as TaskVariableType })
                }
                className="rounded-md px-1.5 py-0.5 text-[11px]"
                style={{
                  background: "transparent",
                  color: "var(--ink-3)",
                  border: "1px solid var(--border)",
                }}
              >
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
              </select>
              <button
                onClick={() => remove(i)}
                title="Remove"
                className="rounded-md p-1"
                style={{
                  background: "transparent",
                  border: 0,
                  color: "var(--ink-3)",
                }}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <Input
            placeholder="name"
            value={v.name}
            onChange={(e) =>
              update(i, { name: e.target.value.replace(/[^a-zA-Z0-9_]/g, "_") })
            }
            style={{ fontSize: 13 }}
          />
          <Input
            placeholder="Label"
            value={v.label}
            onChange={(e) => update(i, { label: e.target.value })}
            style={{ fontSize: 13 }}
          />
          <Input
            placeholder="Default"
            value={String(v.default ?? "")}
            onChange={(e) => update(i, { default: e.target.value })}
            style={{ fontSize: 13 }}
          />
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} className="justify-start">
        <Plus className="h-3.5 w-3.5" /> Add variable
      </Button>
    </div>
  );
}
