import type { ToolStep } from "@/lib/types"

export type ToolArgsProps = {
  args: Record<string, unknown>
  step: ToolStep
}

export type ToolResultProps = {
  result: string
  status: ToolStep["status"]
  step: ToolStep
}

/**
 * Per-tool view configuration.
 *
 * Both renderers are optional — anything not provided falls back to the
 * default JSON / monospace rendering. Keep tool-specific markup inside the
 * renderer file, not in ToolCall, so the chrome stays tool-agnostic.
 */
export type ToolRenderer = {
  Args?: React.ComponentType<ToolArgsProps>
  Result?: React.ComponentType<ToolResultProps>
  /**
   * Optional override for the chrome's "Called <tool>" label. Return a
   * React node to replace the verb + tool-name cluster in the header, or
   * `null` to fall back to default rendering.
   */
  getHeaderLabel?: (step: ToolStep) => React.ReactNode | null
  /** Hide the "Arguments" section entirely when expanded. */
  hideArgs?: boolean
  /**
   * Optional status override. Lets a renderer escalate a "done" call into a
   * "warning" (e.g. SQL returning 0 rows) without changing backend semantics.
   * Return `null` to keep the underlying status.
   */
  getStatusOverride?: (step: ToolStep) => ToolStep["status"] | null
}
