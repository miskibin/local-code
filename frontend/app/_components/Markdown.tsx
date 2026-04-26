"use client";

import { MessageResponse } from "@/components/ai-elements/message";

export function Markdown({ text }: { text: string }) {
  return (
    <div className="lc-markdown text-[15px]" style={{ color: "var(--ink)", lineHeight: "var(--density-line)" }}>
      <MessageResponse>{text}</MessageResponse>
    </div>
  );
}
