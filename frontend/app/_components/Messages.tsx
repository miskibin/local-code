"use client";

import { BookmarkPlus, Copy, Pencil, RotateCcw, Share } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Artifact, AssistantStep, Todo } from "@/lib/types";
import { Markdown } from "./Markdown";
import { PlanCard } from "./PlanCard";
import { Subagent } from "./Subagent";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ToolCall } from "./ToolCall";
import { ArtifactCard } from "./Artifact";

export function UserMessage({
  text,
  onEdit,
}: {
  text: string;
  onEdit?: (text: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!editing) return;
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = ta.scrollHeight + "px";
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
  }, [editing, draft]);

  const startEdit = () => {
    setDraft(text);
    setEditing(true);
  };
  const cancel = () => setEditing(false);
  const save = () => {
    const t = draft.trim();
    if (!t || !onEdit) {
      cancel();
      return;
    }
    setEditing(false);
    onEdit(t);
  };

  if (editing) {
    return (
      <div
        className="flex justify-end"
        style={{ marginBottom: "var(--density-msg-gap)" }}
      >
        <div className="flex max-w-[70%] flex-col items-end gap-2">
          <textarea
            ref={taRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                save();
              } else if (e.key === "Escape") {
                e.preventDefault();
                cancel();
              }
            }}
            className="w-full resize-none whitespace-pre-wrap break-words rounded-[18px] px-4 py-2.5 text-[15px] outline-none"
            style={{
              background: "var(--user-bubble)",
              color: "var(--ink)",
              lineHeight: "var(--density-line)",
              border: "1px solid var(--accent)",
              boxShadow: "0 0 0 3px var(--accent-soft)",
            }}
          />
          <div className="flex gap-2">
            <button
              onClick={cancel}
              className="rounded-md px-3 py-1 text-[13px]"
              style={{
                background: "transparent",
                color: "var(--ink-2)",
                border: "1px solid var(--border)",
              }}
            >
              Cancel
            </button>
            <button
              onClick={save}
              disabled={!draft.trim()}
              className="rounded-md px-3 py-1 text-[13px] text-white"
              style={{
                background: draft.trim()
                  ? "var(--accent)"
                  : "var(--hover-strong)",
                border: 0,
                cursor: draft.trim() ? "pointer" : "not-allowed",
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="group flex items-center justify-end gap-1"
      style={{ marginBottom: "var(--density-msg-gap)" }}
    >
      {onEdit && (
        <button
          title="Edit message"
          onClick={startEdit}
          className="inline-flex h-7 w-7 items-center justify-center rounded-md opacity-0 transition group-hover:opacity-100"
          style={{ color: "var(--ink-3)", background: "transparent" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--hover)";
            e.currentTarget.style.color = "var(--ink)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "var(--ink-3)";
          }}
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      )}
      <div
        className="max-w-[70%] whitespace-pre-wrap break-words rounded-[18px] px-4 py-2.5 text-[15px]"
        style={{
          background: "var(--user-bubble)",
          color: "var(--ink)",
          lineHeight: "var(--density-line)",
        }}
      >
        {text}
      </div>
    </div>
  );
}

function ActionBtn({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className="inline-flex h-7 w-7 items-center justify-center rounded-md transition"
      style={{ color: "var(--ink-3)", background: "transparent" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)";
        e.currentTarget.style.color = "var(--ink)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent";
        e.currentTarget.style.color = "var(--ink-3)";
      }}
    >
      {children}
    </button>
  );
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "step"; step: AssistantStep }
  | { type: "plan"; todos: Todo[]; streaming: boolean };

export function contentBlocksToPlainText(blocks: ContentBlock[]): string {
  return blocks
    .filter((b): b is { type: "text"; text: string } => b.type === "text")
    .map((b) => b.text)
    .join("");
}

export type AssistantMsg = {
  id: string;
  /** Stream order: interleaved user-visible text and tool / subagent blocks */
  contentBlocks: ContentBlock[];
  artifacts?: Artifact[];
};

export function AssistantMessage({
  msg,
  expanded,
  toggleStep,
  isLast,
  streaming,
  savedArtifacts,
  onSaveArtifact,
  onOpenArtifact,
  onCopy,
  onRegenerate,
  onSaveAsTask,
  saveAsTaskBusy,
}: {
  msg: AssistantMsg;
  expanded: Record<string, boolean>;
  toggleStep: (key: string) => void;
  isLast: boolean;
  streaming: boolean;
  savedArtifacts: Record<string, boolean>;
  onSaveArtifact: (a: Artifact) => void;
  onOpenArtifact: (a: Artifact) => void;
  onCopy?: () => void;
  onRegenerate?: () => void;
  onSaveAsTask?: () => void;
  saveAsTaskBusy?: boolean;
}) {
  const plainText = contentBlocksToPlainText(msg.contentBlocks);
  const showThinking = streaming && isLast && !plainText;
  return (
    <div style={{ marginBottom: "var(--density-msg-gap)" }}>
      <div
        className="max-w-full text-[15px]"
        style={{ color: "var(--ink)", lineHeight: "var(--density-line)" }}
      >
        {msg.contentBlocks.map((b, i) =>
          b.type === "text" ? (
            b.text ? <Markdown key={i} text={b.text} /> : null
          ) : b.type === "plan" ? (
            <PlanCard key={i} todos={b.todos} streaming={b.streaming} />
          ) : b.step.kind === "subagent" ? (
            <Subagent
              key={i}
              block={b.step}
              expanded={expanded}
              toggleStep={toggleStep}
              savedArtifacts={savedArtifacts}
              onSaveArtifact={onSaveArtifact}
              onOpenArtifact={onOpenArtifact}
              msgId={msg.id}
              blockIdx={i}
            />
          ) : (
            <ToolCall
              key={i}
              step={b.step}
              expanded={!!expanded[`${msg.id}-block-${i}`]}
              onToggle={() => toggleStep(`${msg.id}-block-${i}`)}
            />
          ),
        )}

        {showThinking && <ThinkingIndicator />}

        {streaming && isLast && plainText && <span className="lc-caret" />}

        {!streaming &&
          msg.artifacts?.map((a) => (
            <ArtifactCard
              key={a.id}
              artifact={a}
              saved={!!savedArtifacts[a.id]}
              onSave={onSaveArtifact}
              onOpen={onOpenArtifact}
            />
          ))}
      </div>

      {!streaming && plainText && (
        <div className="mt-2 flex gap-1" style={{ color: "var(--ink-3)" }}>
          <ActionBtn title="Copy" onClick={onCopy}>
            <Copy className="h-3.5 w-3.5" />
          </ActionBtn>
          <ActionBtn title="Regenerate" onClick={onRegenerate}>
            <RotateCcw className="h-3.5 w-3.5" />
          </ActionBtn>
          {isLast && onSaveAsTask && (
            <ActionBtn
              title={
                saveAsTaskBusy ? "Generating task..." : "Save as task"
              }
              onClick={saveAsTaskBusy ? undefined : onSaveAsTask}
            >
              <BookmarkPlus
                className="h-3.5 w-3.5"
                style={{
                  opacity: saveAsTaskBusy ? 0.4 : 1,
                  animation: saveAsTaskBusy
                    ? "pulse 1.4s ease-in-out infinite"
                    : undefined,
                }}
              />
            </ActionBtn>
          )}
          <ActionBtn title="Share">
            <Share className="h-3.5 w-3.5" />
          </ActionBtn>
        </div>
      )}
    </div>
  );
}
