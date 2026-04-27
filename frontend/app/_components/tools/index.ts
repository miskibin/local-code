import { pythonExecRenderer } from "./python-exec";
import { readFileRenderer } from "./read-file";
import { webFetchRenderer } from "./web-fetch";
import type { ToolRenderer } from "./types";

/**
 * Per-tool view registry.
 *
 * To add a new tool:
 *  1. Create `<tool-slug>.tsx` exporting a `ToolRenderer`.
 *  2. Add one entry below.
 *
 * `ToolCall` looks the tool up by name and falls back to default renderers
 * for any field the tool doesn't override. Keep tool chrome in `ToolCall`,
 * tool-specific markup in the renderer file.
 */
const REGISTRY: Record<string, ToolRenderer> = {
  python_exec: pythonExecRenderer,
  read_file: readFileRenderer,
  web_fetch: webFetchRenderer,
};

const EMPTY_RENDERER: ToolRenderer = {};

export function getToolRenderer(toolName: string): ToolRenderer {
  return REGISTRY[toolName] ?? EMPTY_RENDERER;
}

export type { ToolRenderer, ToolArgsProps, ToolResultProps } from "./types";
