"use client";

import { ExternalLink } from "lucide-react";
import type { ToolArgsProps, ToolRenderer } from "./types";
import { DefaultArgs } from "./default";

function WebFetchArgs({ args, step }: ToolArgsProps) {
  const url = typeof args?.url === "string" ? args.url : "";
  if (!url) return <DefaultArgs args={args} step={step} />;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="inline-flex max-w-full items-center gap-2 truncate rounded-lg px-2.5 py-2"
      style={{
        background: "var(--bg-soft)",
        border: "1px solid var(--border)",
        color: "var(--accent-ink)",
        fontFamily: "var(--font-mono)",
        fontSize: 12.5,
      }}
    >
      <ExternalLink className="h-3.5 w-3.5 flex-shrink-0" />
      <span className="truncate">{url}</span>
    </a>
  );
}

export const webFetchRenderer: ToolRenderer = {
  Args: WebFetchArgs,
};
