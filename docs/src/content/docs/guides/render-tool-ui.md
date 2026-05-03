---
title: Render a custom tool UI
description: Add a React component for a specific tool's output in the chat stream.
---

By default, tool output is rendered with a generic JSON-blob viewer. To
give a tool a bespoke UI, add a component to the registry.

## 1. Build the component

```tsx
// frontend/app/_components/tools/TimezoneNowTool.tsx
"use client";

import type { ToolPartProps } from "./types";

export function TimezoneNowTool({ part }: ToolPartProps) {
  if (part.state !== "output-available") return null;
  const value = part.output as string;
  return (
    <div className="rounded-md border bg-card px-3 py-2 text-sm font-mono">
      {value}
    </div>
  );
}
```

`ToolPartProps` already gives you the AI SDK tool part with its
`state` ("input-available" / "output-available" / "output-error") and
the `input` / `output` payloads.

## 2. Register it

```ts
// frontend/app/_components/tools/index.ts
import { TimezoneNowTool } from "./TimezoneNowTool";

export const toolComponents: Record<string, ComponentType<ToolPartProps>> = {
  // ...
  timezone_now: TimezoneNowTool,
};
```

The map's key is the tool's `name` (matches the Python `BaseTool.name`).

## 3. Subagent nesting (free)

If your tool runs inside a subagent (`task` dispatcher), the rendering
tree groups it under the parent tool call automatically — no work needed
in your component. `getParentToolCallId` in `ChatView.tsx` handles that.

## Don't

- Don't read `useChat` state from inside a tool component — it gets the
  part as a prop. Side-effects should live higher up.
- Don't fetch from the backend in the render path. If you need extra
  data, add it to the tool's output server-side.
- Don't add fallback markup that hides errors. If `state ===
  "output-error"`, render the error.
