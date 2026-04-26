"use client";

import { Loader2 } from "lucide-react";

export function ThinkingIndicator({ label = "Thinking" }: { label?: string }) {
  return (
    <div
      className="inline-flex items-center gap-2 py-1.5 text-[13px]"
      style={{ color: "var(--ink-3)" }}
    >
      <Loader2 className="lc-spin h-3.5 w-3.5" />
      <span>{label}</span>
      <span>
        <span className="lc-dot" />
        <span className="lc-dot" />
        <span className="lc-dot" />
      </span>
    </div>
  );
}
