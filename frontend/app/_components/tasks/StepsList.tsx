"use client";

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { nanoid } from "nanoid";
import type { TaskStep, TaskStepKind } from "@/lib/types";
import { Button } from "@/components/ui/button";

type Props = {
  steps: TaskStep[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onChange: (next: TaskStep[]) => void;
};

const KIND_LABEL: Record<TaskStepKind, string> = {
  tool: "TOOL",
  code: "CODE",
  subagent: "SUBAGENT",
  prompt: "PROMPT",
};

const KIND_COLOR: Record<TaskStepKind, string> = {
  tool: "var(--accent)",
  code: "#9333ea",
  subagent: "#0ea5e9",
  prompt: "#10b981",
};

function makeStep(kind: TaskStepKind, index: number): TaskStep {
  const id = `s${index + 1}_${nanoid(4)}`;
  return {
    id,
    kind,
    title: `Step ${index + 1}`,
    server: kind === "tool" ? "" : null,
    tool: kind === "tool" ? "" : null,
    args_template: kind === "tool" ? {} : null,
    code: kind === "code" ? "" : null,
    subagent: kind === "subagent" ? "" : null,
    prompt: kind === "subagent" || kind === "prompt" ? "" : null,
    output_name: "output",
    output_kind: "text",
    inputs: [],
  };
}

export function StepsList({ steps, selectedId, onSelect, onChange }: Props) {
  const move = (idx: number, delta: number) => {
    const next = [...steps];
    const target = idx + delta;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    onChange(next);
  };

  const remove = (idx: number) => {
    const next = steps.filter((_, i) => i !== idx);
    onChange(next);
  };

  const addStep = (kind: TaskStepKind) => {
    const next = [...steps, makeStep(kind, steps.length)];
    onChange(next);
    onSelect(next[next.length - 1].id);
  };

  return (
    <div className="flex flex-col gap-1.5">
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
        <span>Steps {steps.length}</span>
      </div>
      {steps.map((s, i) => (
        <div
          key={s.id}
          className="group/row flex items-center gap-2 rounded-md px-2 py-1.5"
          style={{
            background:
              selectedId === s.id ? "var(--hover-strong)" : "transparent",
            border:
              selectedId === s.id
                ? "1px solid var(--accent-soft)"
                : "1px solid transparent",
            cursor: "pointer",
          }}
          onClick={() => onSelect(s.id)}
        >
          <span
            className="rounded px-1.5 py-0.5"
            style={{
              fontSize: 11,
              background: "var(--hover)",
              color: "var(--ink-3)",
              minWidth: 20,
              textAlign: "center",
            }}
          >
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <div
              className="truncate"
              style={{ fontSize: 13, color: "var(--ink)" }}
            >
              {s.title || "(untitled)"}
            </div>
            <div
              style={{
                fontSize: 10,
                fontWeight: 500,
                letterSpacing: ".04em",
                color: KIND_COLOR[s.kind],
              }}
            >
              {KIND_LABEL[s.kind]}
            </div>
          </div>
          <div className="flex opacity-0 transition group-hover/row:opacity-100">
            <button
              title="Move up"
              onClick={(e) => {
                e.stopPropagation();
                move(i, -1);
              }}
              className="rounded p-1"
              style={{ background: "transparent", border: 0, color: "var(--ink-3)" }}
            >
              <ArrowUp className="h-3 w-3" />
            </button>
            <button
              title="Move down"
              onClick={(e) => {
                e.stopPropagation();
                move(i, 1);
              }}
              className="rounded p-1"
              style={{ background: "transparent", border: 0, color: "var(--ink-3)" }}
            >
              <ArrowDown className="h-3 w-3" />
            </button>
            <button
              title="Delete"
              onClick={(e) => {
                e.stopPropagation();
                remove(i);
              }}
              className="rounded p-1"
              style={{ background: "transparent", border: 0, color: "var(--ink-3)" }}
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        </div>
      ))}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {(["tool", "code", "subagent", "prompt"] as TaskStepKind[]).map((k) => (
          <Button
            key={k}
            variant="outline"
            size="sm"
            onClick={() => addStep(k)}
            className="h-7 text-[11px]"
          >
            <Plus className="h-3 w-3" />
            {KIND_LABEL[k]}
          </Button>
        ))}
      </div>
    </div>
  );
}
