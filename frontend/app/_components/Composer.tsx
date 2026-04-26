"use client";

import { ArrowUp, Plus, Square, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ModelPicker } from "./ModelPicker";

export function Composer({
  onSend,
  onStop,
  streaming,
  model,
  onModelChange,
}: {
  onSend: (text: string) => void;
  onStop?: () => void;
  streaming: boolean;
  model?: string;
  onModelChange?: (m: string) => void;
}) {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const capped = ta.scrollHeight > 200;
    ta.style.height = (capped ? 200 : ta.scrollHeight) + "px";
    ta.style.overflowY = capped ? "auto" : "hidden";
  }, [text]);

  const submit = () => {
    const t = text.trim();
    if (!t || streaming) return;
    onSend(t);
    setText("");
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-8 pb-4 pt-1">
      <div
        className="rounded-3xl px-3.5 pt-2.5 pb-2 transition"
        style={{
          background: "#fff",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 0 rgba(0,0,0,.02)",
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = "var(--accent)";
          e.currentTarget.style.boxShadow = "0 0 0 3px var(--accent-soft)";
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = "var(--border)";
          e.currentTarget.style.boxShadow = "0 1px 0 rgba(0,0,0,.02)";
        }}
      >
        <textarea
          ref={taRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask anything"
          aria-label="Message"
          className="lc-composer"
          style={{ minHeight: 24, padding: "6px 0" }}
          disabled={streaming}
        />
        <div className="mt-1 flex items-center justify-between gap-2">
          <div className="flex items-center gap-0.5">
            <ToolbarBtn title="Attach">
              <Plus className="h-4 w-4" />
            </ToolbarBtn>
            <ToolbarBtn title="Tools">
              <Wrench className="h-3.5 w-3.5" />
              <span className="ml-1.5 text-[13px]">Tools</span>
            </ToolbarBtn>
            <ModelPicker value={model} onChange={onModelChange} />
          </div>
          <div className="flex items-center gap-1">
            {streaming ? (
              <button
                onClick={onStop}
                title="Stop"
                className="grid h-8 w-8 place-items-center rounded-full text-white"
                style={{ background: "var(--ink)", border: 0, cursor: "pointer" }}
              >
                <Square className="h-3 w-3" />
              </button>
            ) : (
              <button
                onClick={submit}
                disabled={!text.trim()}
                title="Send"
                className="grid h-8 w-8 place-items-center rounded-full text-white transition"
                style={{
                  background: text.trim() ? "var(--accent)" : "var(--hover-strong)",
                  border: 0,
                  cursor: text.trim() ? "pointer" : "not-allowed",
                }}
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolbarBtn({
  title,
  children,
  onClick,
}: {
  title: string;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      type="button"
      className="inline-flex items-center rounded-md px-2 py-1.5"
      style={{ background: "transparent", border: 0, color: "var(--ink-2)" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent";
      }}
    >
      {children}
    </button>
  );
}
