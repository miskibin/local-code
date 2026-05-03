---
title: Render a custom tool UI
description: Map a tool name to a React component.
---

```tsx
// frontend/app/_components/tools/TimezoneNowTool.tsx
"use client";
import type { ToolPartProps } from "./types";

export function TimezoneNowTool({ part }: ToolPartProps) {
  if (part.state !== "output-available") return null;
  return (
    <div className="rounded-md border bg-card px-3 py-2 font-mono text-sm">
      {part.output as string}
    </div>
  );
}
```

```ts
// frontend/app/_components/tools/index.ts
import { TimezoneNowTool } from "./TimezoneNowTool";

export const toolComponents = {
  // ...
  timezone_now: TimezoneNowTool,
};
```

Map key = the Python `BaseTool.name`. No registration → generic JSON
renderer.

Subagent grouping is handled higher up — your component just renders one
part.

## Don't

- Don't fetch from inside a tool component. If you need extra data,
  return it from the tool server-side.
- Don't hide errors. If `part.state === "output-error"`, render it.
