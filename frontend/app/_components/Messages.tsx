"use client"

import {
  ArrowDown,
  ArrowUp,
  BookmarkPlus,
  Copy,
  Database,
  ExternalLink,
  FileText,
  ImageIcon,
  Pencil,
  RotateCcw,
  Share,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import type { Artifact, AssistantStep, Todo } from "@/lib/types"
import { Markdown } from "./Markdown"
import { PlanCard } from "./PlanCard"
import { QuizCard } from "./QuizCard"
import { Subagent } from "./Subagent"
import { ThinkingIndicator } from "./ThinkingIndicator"
import { ToolCall } from "./ToolCall"

export type UserAttachment = {
  artifactId: string
  mediaType: string
  name?: string
}

export function UserMessage({
  text,
  attachments,
  onOpenAttachment,
  onEdit,
}: {
  text: string
  attachments?: UserAttachment[]
  onOpenAttachment?: (artifactId: string) => void
  onEdit?: (text: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(text)
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!editing) return
    const ta = taRef.current
    if (!ta) return
    ta.style.height = "auto"
    ta.style.height = ta.scrollHeight + "px"
    ta.focus()
    ta.setSelectionRange(ta.value.length, ta.value.length)
  }, [editing, draft])

  const startEdit = () => {
    setDraft(text)
    setEditing(true)
  }
  const cancel = () => setEditing(false)
  const save = () => {
    const t = draft.trim()
    if (!t || !onEdit) {
      cancel()
      return
    }
    setEditing(false)
    onEdit(t)
  }

  if (editing) {
    return (
      <div
        className="flex justify-end"
        style={{ marginBottom: "var(--density-msg-gap)" }}
      >
        <div className="flex w-full max-w-[70%] min-w-0 flex-col gap-2">
          <textarea
            ref={taRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault()
                save()
              } else if (e.key === "Escape") {
                e.preventDefault()
                cancel()
              }
            }}
            className="min-h-0 w-full min-w-0 resize-none rounded-[18px] px-4 py-2.5 text-[15px] break-words whitespace-pre-wrap outline-none"
            style={{
              background: "var(--user-bubble)",
              color: "var(--ink)",
              lineHeight: "var(--density-line)",
              border: "1px solid var(--accent)",
              boxShadow: "0 0 0 3px var(--accent-soft)",
            }}
          />
          <div className="flex justify-end gap-2">
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
              className="rounded-md px-3 py-1 text-[13px] text-accent-foreground"
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
    )
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
            e.currentTarget.style.background = "var(--hover)"
            e.currentTarget.style.color = "var(--ink)"
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent"
            e.currentTarget.style.color = "var(--ink-3)"
          }}
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      )}
      <div className="flex max-w-[70%] flex-col items-end gap-1.5">
        {attachments && attachments.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1.5">
            {attachments.map((a) => (
              <UserAttachmentChip
                key={a.artifactId}
                attachment={a}
                onOpen={
                  onOpenAttachment
                    ? () => onOpenAttachment(a.artifactId)
                    : undefined
                }
              />
            ))}
          </div>
        )}
        {text && (
          <div
            className="rounded-[18px] px-4 py-2.5 text-[15px] break-words whitespace-pre-wrap"
            style={{
              background: "var(--user-bubble)",
              color: "var(--ink)",
              lineHeight: "var(--density-line)",
            }}
          >
            {text}
          </div>
        )}
      </div>
    </div>
  )
}

function UserAttachmentChip({
  attachment,
  onOpen,
}: {
  attachment: UserAttachment
  onOpen?: () => void
}) {
  const isImage = attachment.mediaType.startsWith("image/")
  const isTable =
    attachment.mediaType === "text/csv" ||
    attachment.mediaType === "application/csv" ||
    attachment.mediaType === "text/tab-separated-values" ||
    /\.(csv|tsv)$/i.test(attachment.name ?? "")
  const Icon = isImage ? ImageIcon : isTable ? Database : FileText
  return (
    <button
      type="button"
      onClick={onOpen}
      className="inline-flex max-w-[260px] items-center gap-2 rounded-md px-2 py-1 text-[12px]"
      style={{
        background: "var(--user-bubble)",
        border: "1px solid var(--border)",
        color: "var(--ink)",
        cursor: onOpen ? "pointer" : "default",
      }}
      title={attachment.name ?? attachment.artifactId}
    >
      <Icon
        className="h-3.5 w-3.5 flex-shrink-0"
        style={{ color: "var(--accent)" }}
      />
      <span className="truncate">
        {attachment.name ?? attachment.artifactId}
      </span>
    </button>
  )
}

function ActionBtn({
  title,
  onClick,
  children,
}: {
  title: string
  onClick?: () => void
  children: React.ReactNode
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className="inline-flex h-7 w-7 items-center justify-center rounded-md transition"
      style={{ color: "var(--ink-3)", background: "transparent" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
        e.currentTarget.style.color = "var(--ink)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
        e.currentTarget.style.color = "var(--ink-3)"
      }}
    >
      {children}
    </button>
  )
}

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "step"; step: AssistantStep }
  | { type: "plan"; todos: Todo[]; streaming: boolean }
  | {
      type: "quiz"
      toolCallId: string
      question: string
      options: string[]
      allowCustom: boolean
      status: "running" | "done" | "error"
      answer?: string
    }

export function contentBlocksToPlainText(blocks: ContentBlock[]): string {
  return blocks
    .filter((b): b is { type: "text"; text: string } => b.type === "text")
    .map((b) => b.text)
    .join("")
}

export type AssistantMsg = {
  id: string
  /** Stream order: interleaved user-visible text and tool / subagent blocks */
  contentBlocks: ContentBlock[]
  artifacts?: Artifact[]
  usage?: { inputTokens: number; outputTokens: number; durationMs?: number }
  summaryFired?: boolean
  traceId?: string
  traceUrl?: string
  initialFeedback?: 0 | 1
}

export function formatTokens(n: number): string {
  if (n < 1000) return String(n)
  if (n < 10_000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k"
  return Math.round(n / 1000) + "k"
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1).replace(/\.0$/, "")}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s - m * 60)
  return `${m}m${rem ? ` ${rem}s` : ""}`
}

function UsageRow({ usage }: { usage: NonNullable<AssistantMsg["usage"]> }) {
  const { inputTokens, outputTokens, durationMs } = usage
  if (!inputTokens && !outputTokens && !durationMs) return null
  return (
    <div
      className="flex items-center gap-2 text-[11px] tabular-nums"
      style={{ color: "var(--ink-3)" }}
      aria-label="Token usage"
    >
      {inputTokens > 0 && (
        <span className="inline-flex items-center gap-0.5" title="Input tokens">
          <ArrowDown className="h-3 w-3" />
          {formatTokens(inputTokens)}
        </span>
      )}
      {outputTokens > 0 && (
        <span
          className="inline-flex items-center gap-0.5"
          title="Output tokens"
        >
          <ArrowUp className="h-3 w-3" />
          {formatTokens(outputTokens)}
        </span>
      )}
      {typeof durationMs === "number" && durationMs > 0 && (
        <span title="Total time">{formatDuration(durationMs)}</span>
      )}
    </div>
  )
}

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
  onQuizAnswer,
  onFeedback,
}: {
  msg: AssistantMsg
  expanded: Record<string, boolean>
  toggleStep: (key: string) => void
  isLast: boolean
  streaming: boolean
  savedArtifacts: Record<string, boolean>
  onSaveArtifact: (a: Artifact) => void
  onOpenArtifact: (a: Artifact) => void
  onCopy?: () => void
  onRegenerate?: () => void
  onSaveAsTask?: () => void
  saveAsTaskBusy?: boolean
  onQuizAnswer?: (toolCallId: string, value: string) => void
  onFeedback?: (value: 0 | 1) => void
}) {
  const plainText = contentBlocksToPlainText(msg.contentBlocks)
  const showThinking = streaming && isLast && !plainText
  const [sentFeedback, setSentFeedback] = useState<0 | 1 | null>(
    msg.initialFeedback ?? null
  )
  useEffect(() => {
    setSentFeedback(msg.initialFeedback ?? null)
  }, [msg.traceId, msg.initialFeedback])
  const submitFeedback = (value: 0 | 1) => {
    if (sentFeedback !== null || !onFeedback) return
    setSentFeedback(value)
    onFeedback(value)
    toast.success(value === 1 ? "Thanks for the feedback" : "Feedback noted")
  }
  return (
    <div style={{ marginBottom: "var(--density-msg-gap)" }}>
      {msg.summaryFired && (
        <div
          className="mb-2 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11.5px]"
          style={{
            background: "var(--amber-soft, #fef3c7)",
            color: "var(--amber, #b45309)",
            border: "1px solid var(--amber, #f59e0b)",
          }}
          title="Older messages were summarized to free context space"
        >
          <span>🗜</span>
          <span>Conversation auto-compacted</span>
        </div>
      )}
      <div
        className="max-w-full text-[15px]"
        style={{ color: "var(--ink)", lineHeight: "var(--density-line)" }}
      >
        {msg.contentBlocks.map((b, i) =>
          b.type === "text" ? (
            b.text ? (
              <Markdown key={i} text={b.text} />
            ) : null
          ) : b.type === "plan" ? (
            <PlanCard key={i} todos={b.todos} streaming={b.streaming} />
          ) : b.type === "quiz" ? (
            <QuizCard
              key={`quiz-${b.toolCallId}`}
              toolCallId={b.toolCallId}
              question={b.question}
              options={b.options}
              allowCustom={b.allowCustom}
              status={b.status}
              answer={b.answer}
              onSubmit={onQuizAnswer}
            />
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
              toolCallId={b.step.toolCallId}
              expanded={!!expanded[`${msg.id}-block-${i}`]}
              onToggle={() => toggleStep(`${msg.id}-block-${i}`)}
            />
          )
        )}

        {showThinking && <ThinkingIndicator />}

        {streaming && isLast && plainText && <span className="lc-caret" />}
      </div>

      {!streaming && plainText && (
        <div
          className="mt-2 flex items-center gap-3"
          style={{ color: "var(--ink-3)" }}
        >
          <div className="flex gap-1">
            <ActionBtn title="Copy" onClick={onCopy}>
              <Copy className="h-3.5 w-3.5" />
            </ActionBtn>
            <ActionBtn title="Regenerate" onClick={onRegenerate}>
              <RotateCcw className="h-3.5 w-3.5" />
            </ActionBtn>
            {msg.traceId && onFeedback && (
              <>
                <ActionBtn
                  title={
                    sentFeedback === 1
                      ? "Feedback sent"
                      : sentFeedback === 0
                        ? "Feedback already sent"
                        : "Good response"
                  }
                  onClick={
                    sentFeedback === null ? () => submitFeedback(1) : undefined
                  }
                >
                  <ThumbsUp
                    className="h-3.5 w-3.5"
                    style={{
                      color: sentFeedback === 1 ? "var(--ink)" : "var(--ink-3)",
                      fill: sentFeedback === 1 ? "var(--ink)" : "none",
                      opacity: sentFeedback === 0 ? 0.35 : 1,
                    }}
                  />
                </ActionBtn>
                <ActionBtn
                  title={
                    sentFeedback === 0
                      ? "Feedback sent"
                      : sentFeedback === 1
                        ? "Feedback already sent"
                        : "Bad response"
                  }
                  onClick={
                    sentFeedback === null ? () => submitFeedback(0) : undefined
                  }
                >
                  <ThumbsDown
                    className="h-3.5 w-3.5"
                    style={{
                      color: sentFeedback === 0 ? "var(--ink)" : "var(--ink-3)",
                      fill: sentFeedback === 0 ? "var(--ink)" : "none",
                      opacity: sentFeedback === 1 ? 0.35 : 1,
                    }}
                  />
                </ActionBtn>
                {msg.traceUrl && (
                  <ActionBtn
                    title="Open trace in Langfuse"
                    onClick={() =>
                      window.open(msg.traceUrl, "_blank", "noopener,noreferrer")
                    }
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </ActionBtn>
                )}
              </>
            )}
            {isLast && onSaveAsTask && (
              <ActionBtn
                title={saveAsTaskBusy ? "Generating task..." : "Save as task"}
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
          {msg.usage && <UsageRow usage={msg.usage} />}
        </div>
      )}
    </div>
  )
}
