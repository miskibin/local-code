import type { ToolStep } from "@/lib/types";

export type ToolArgsProps = {
  args: Record<string, unknown>;
  step: ToolStep;
};

export type ToolResultProps = {
  result: string;
  status: ToolStep["status"];
  step: ToolStep;
};

/**
 * Per-tool view configuration.
 *
 * Both renderers are optional — anything not provided falls back to the
 * default JSON / monospace rendering. Keep tool-specific markup inside the
 * renderer file, not in ToolCall, so the chrome stays tool-agnostic.
 */
export type ToolRenderer = {
  Args?: React.ComponentType<ToolArgsProps>;
  Result?: React.ComponentType<ToolResultProps>;
};
