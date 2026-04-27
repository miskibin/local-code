"use client"

import {
  Database,
  FileText,
  ImageIcon,
  Paperclip,
  Square,
  X,
} from "lucide-react"
import type { LanguageModelUsage } from "ai"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import {
  Context,
  ContextCacheUsage,
  ContextContent,
  ContextContentBody,
  ContextContentFooter,
  ContextContentHeader,
  ContextInputUsage,
  ContextOutputUsage,
  ContextReasoningUsage,
  ContextTrigger,
} from "@/components/ai-elements/context"
import { api } from "@/lib/api"
import type { Artifact } from "@/lib/types"
import type { UsageDataPart } from "./ChatView"
import { ModelPicker } from "./ModelPicker"

type Props = {
  onSend: (text: string, attachments: Artifact[]) => void
  onStop?: () => void
  streaming: boolean
  model?: string
  onModelChange?: (m: string) => void
  sessionId: string
  onAttachmentUploaded?: (a: Artifact) => void
  usage?: UsageDataPart
}

export function Composer({
  onSend,
  onStop,
  streaming,
  model,
  onModelChange,
  sessionId,
  onAttachmentUploaded,
  usage,
}: Props) {
  const [text, setText] = useState("")
  const [pending, setPending] = useState<Artifact[]>([])
  const [uploading, setUploading] = useState(0)
  const [dragOver, setDragOver] = useState(false)
  const taRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = "auto"
    const capped = ta.scrollHeight > 200
    ta.style.height = (capped ? 200 : ta.scrollHeight) + "px"
    ta.style.overflowY = capped ? "auto" : "hidden"
  }, [text])

  const upload = async (files: File[] | FileList | null) => {
    if (!files) return
    const list = Array.from(files)
    if (list.length === 0) return
    setUploading((n) => n + list.length)
    try {
      const uploaded = await Promise.all(
        list.map((f) =>
          api.uploadArtifact(f, sessionId).catch((e) => {
            toast.error("Upload failed", {
              description: e instanceof Error ? e.message : String(e),
            })
            return null
          })
        )
      )
      const ok = uploaded.filter((a): a is Artifact => !!a)
      setPending((p) => [...p, ...ok])
      for (const a of ok) onAttachmentUploaded?.(a)
    } finally {
      setUploading((n) => n - list.length)
    }
  }

  const submit = () => {
    const t = text.trim()
    if ((!t && pending.length === 0) || streaming || uploading > 0) return
    onSend(t, pending)
    setText("")
    setPending([])
  }

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (!e.clipboardData?.files?.length) return
    e.preventDefault()
    void upload(e.clipboardData.files)
  }

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer?.files?.length) void upload(e.dataTransfer.files)
  }

  const removeAttachment = (id: string) =>
    setPending((p) => p.filter((a) => a.id !== id))

  const canSend =
    (text.trim().length > 0 || pending.length > 0) &&
    !streaming &&
    uploading === 0

  return (
    <div className="mx-auto w-full max-w-4xl px-8 pt-1 pb-4">
      <div
        className="rounded-3xl px-3.5 pt-2.5 pb-2 transition"
        style={{
          background: "var(--surface)",
          border: dragOver
            ? "1px solid var(--accent)"
            : "1px solid var(--border)",
          boxShadow: dragOver
            ? "0 0 0 3px var(--accent-soft)"
            : "0 1px 0 rgba(0,0,0,.02)",
        }}
        onDragOver={(e) => {
          e.preventDefault()
          if (e.dataTransfer?.types?.includes("Files")) setDragOver(true)
        }}
        onDragLeave={(e) => {
          if (e.currentTarget.contains(e.relatedTarget as Node)) return
          setDragOver(false)
        }}
        onDrop={onDrop}
      >
        {(pending.length > 0 || uploading > 0) && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {pending.map((a) => (
              <AttachmentChip
                key={a.id}
                artifact={a}
                onRemove={() => removeAttachment(a.id)}
              />
            ))}
            {uploading > 0 && (
              <div
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px]"
                style={{
                  background: "var(--hover)",
                  color: "var(--ink-2)",
                }}
              >
                Uploading {uploading}…
              </div>
            )}
          </div>
        )}
        <textarea
          ref={taRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          onPaste={onPaste}
          placeholder="Ask anything"
          aria-label="Message"
          className="lc-composer"
          style={{ minHeight: 24, padding: "6px 0" }}
          disabled={streaming}
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            void upload(e.target.files)
            e.target.value = ""
          }}
        />
        <div className="mt-1 flex items-center justify-between gap-2">
          <div className="flex items-center gap-0.5">
            <ToolbarBtn
              title="Attach file"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="h-4 w-4" />
            </ToolbarBtn>
            <ModelPicker value={model} onChange={onModelChange} />
            {usage && usage.contextMaxTokens && usage.contextMaxTokens > 0 ? (
              <Context
                usedTokens={usage.inputTokens}
                maxTokens={usage.contextMaxTokens}
                modelId={usage.modelId}
                usage={
                  {
                    inputTokens: usage.inputTokens,
                    outputTokens: usage.outputTokens,
                    totalTokens: usage.inputTokens + usage.outputTokens,
                  } as LanguageModelUsage
                }
              >
                <ContextTrigger />
                <ContextContent>
                  <ContextContentHeader />
                  <ContextContentBody>
                    <ContextInputUsage />
                    <ContextOutputUsage />
                    <ContextReasoningUsage />
                    <ContextCacheUsage />
                  </ContextContentBody>
                  {usage.modelId ? <ContextContentFooter /> : null}
                </ContextContent>
              </Context>
            ) : null}
          </div>
          <div className="flex items-center gap-1">
            {streaming ? (
              <button
                onClick={onStop}
                title="Stop"
                className="inline-flex items-center justify-center gap-1.5 transition"
                style={{
                  height: 28,
                  minWidth: 44,
                  padding: "0 10px",
                  borderRadius: 6,
                  fontFamily: "var(--font-mono)",
                  background: "var(--accent)",
                  border: "1px solid var(--accent)",
                  color: "var(--accent-foreground)",
                  cursor: "pointer",
                }}
              >
                <Square
                  className="h-2.5 w-2.5"
                  style={{ fill: "currentColor" }}
                />
                <span style={{ fontSize: 11 }}>stop</span>
              </button>
            ) : (
              <button
                onClick={submit}
                disabled={!canSend}
                title="Send (Enter)"
                className="inline-flex items-center justify-center gap-1.5 transition"
                style={{
                  height: 28,
                  minWidth: 44,
                  padding: "0 10px",
                  borderRadius: 6,
                  fontFamily: "var(--font-mono)",
                  background: canSend ? "var(--accent)" : "var(--accent-soft)",
                  border: canSend
                    ? "1px solid var(--accent)"
                    : "1px solid color-mix(in oklab, var(--accent) 32%, var(--border))",
                  color: canSend
                    ? "var(--accent-foreground)"
                    : "var(--accent-ink)",
                  cursor: canSend ? "pointer" : "not-allowed",
                  opacity: 1,
                }}
              >
                <span style={{ fontSize: 13 }}>↵</span>
                <span style={{ fontSize: 11 }}>send</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function AttachmentChip({
  artifact,
  onRemove,
}: {
  artifact: Artifact
  onRemove: () => void
}) {
  const Icon =
    artifact.kind === "image"
      ? ImageIcon
      : artifact.kind === "table"
        ? Database
        : FileText
  const subtitle = artifact.summary || artifact.kind
  return (
    <div
      className="group inline-flex max-w-[260px] items-center gap-2 rounded-md px-2 py-1 text-[12px]"
      style={{
        background: "var(--hover)",
        border: "1px solid var(--border)",
      }}
      title={`${artifact.title} — ${subtitle}`}
    >
      <Icon
        className="h-3.5 w-3.5 flex-shrink-0"
        style={{ color: "var(--accent)" }}
      />
      <span className="flex-1 truncate" style={{ color: "var(--ink)" }}>
        {artifact.title}
      </span>
      <button
        type="button"
        onClick={onRemove}
        title="Remove"
        className="grid h-4 w-4 place-items-center rounded-full"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-3)",
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  )
}

function ToolbarBtn({
  title,
  children,
  onClick,
}: {
  title: string
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      type="button"
      className="inline-flex items-center rounded-md px-2 py-1.5"
      style={{ background: "transparent", border: 0, color: "var(--ink-2)" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      {children}
    </button>
  )
}
