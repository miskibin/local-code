"use client"

import {
  Check,
  Copy,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Loader2,
  Mail,
  Table as TableIcon,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { api } from "@/lib/api"
import { useAuthOptional } from "@/lib/auth"
import type {
  Artifact,
  ArtifactImagePayload,
  ArtifactTablePayload,
  ArtifactTextPayload,
} from "@/lib/types"
import { downloadImagePng } from "./ArtifactImage"
import { downloadTableCsv } from "./ArtifactTable"

export type EmailDraftCardProps = {
  toolCallId: string
  to: string
  subject: string
  body: string
  cc: string[]
  bcc: string[]
  attachmentArtifactIds: string[]
  status: "running" | "done" | "error"
}

type MailtoInput = {
  to: string
  subject: string
  body: string
  cc: string[]
  bcc: string[]
}

function buildMailto(p: MailtoInput): string {
  const enc = encodeURIComponent
  const parts: string[] = []
  if (p.subject) parts.push(`subject=${enc(p.subject)}`)
  if (p.body) parts.push(`body=${enc(p.body)}`)
  if (p.cc.length) parts.push(`cc=${enc(p.cc.join(","))}`)
  if (p.bcc.length) parts.push(`bcc=${enc(p.bcc.join(","))}`)
  return `mailto:${enc(p.to)}${parts.length ? `?${parts.join("&")}` : ""}`
}

function buildPlainText(p: EmailDraftCardProps, fromEmail: string): string {
  const lines: string[] = []
  if (fromEmail) lines.push(`From: ${fromEmail}`)
  lines.push(`To: ${p.to}`)
  if (p.cc.length) lines.push(`Cc: ${p.cc.join(", ")}`)
  if (p.bcc.length) lines.push(`Bcc: ${p.bcc.join(", ")}`)
  lines.push(`Subject: ${p.subject}`)
  lines.push("")
  lines.push(p.body)
  return lines.join("\n")
}

function downloadTextArtifact(artifact: Artifact): void {
  const payload = artifact.payload as ArtifactTextPayload
  const text = payload.text ?? payload.text_preview ?? ""
  const safe =
    (artifact.title || "text").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 120) +
    ".txt"
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = safe
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function triggerArtifactDownload(artifact: Artifact): void {
  if (artifact.kind === "table") {
    downloadTableCsv(artifact.payload as ArtifactTablePayload, artifact.title)
    return
  }
  if (artifact.kind === "image") {
    downloadImagePng(artifact.payload as ArtifactImagePayload, artifact.title)
    return
  }
  downloadTextArtifact(artifact)
}

function KindIcon({ kind }: { kind: Artifact["kind"] }) {
  if (kind === "table") return <TableIcon className="h-3.5 w-3.5" />
  if (kind === "image") return <ImageIcon className="h-3.5 w-3.5" />
  return <FileText className="h-3.5 w-3.5" />
}

type AttachmentEntry =
  | { id: string; status: "loading" }
  | { id: string; status: "ready"; artifact: Artifact }
  | { id: string; status: "error" }

export function EmailDraftCard(props: EmailDraftCardProps) {
  const auth = useAuthOptional()
  const fromEmail = auth?.user?.email ?? ""
  const [copied, setCopied] = useState(false)
  const [attachments, setAttachments] = useState<AttachmentEntry[]>(() =>
    props.attachmentArtifactIds.map((id) => ({
      id,
      status: "loading" as const,
    }))
  )
  const lastIdsRef = useRef<string>(props.attachmentArtifactIds.join("|"))

  useEffect(() => {
    const key = props.attachmentArtifactIds.join("|")
    if (key === lastIdsRef.current && attachments.length > 0) return
    lastIdsRef.current = key
    setAttachments(
      props.attachmentArtifactIds.map((id) => {
        const existing = attachments.find((a) => a.id === id)
        return existing ?? { id, status: "loading" as const }
      })
    )
     
    let cancelled = false
    for (const id of props.attachmentArtifactIds) {
      api
        .getArtifact(id)
        .then((artifact) => {
          if (cancelled) return
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id ? { id, status: "ready", artifact } : a
            )
          )
        })
        .catch(() => {
          if (cancelled) return
          setAttachments((prev) =>
            prev.map((a) => (a.id === id ? { id, status: "error" } : a))
          )
        })
    }
     
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- attachments is intentionally read for cache reuse
  }, [props.attachmentArtifactIds])

  const running = props.status === "running"
  const errored = props.status === "error"

  const onCopy = async () => {
    await navigator.clipboard.writeText(buildPlainText(props, fromEmail))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const onRemoveAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id))
  }

  const onOpenInMail = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (running) {
      e.preventDefault()
      return
    }
    for (const a of attachments) {
      if (a.status === "ready") triggerArtifactDownload(a.artifact)
    }
  }

  const pill = errored
    ? { label: "Drafting failed", color: "var(--red)", bg: "var(--red-soft)" }
    : running
      ? { label: "Drafting…", color: "var(--accent)", bg: "var(--accent-soft)" }
      : {
          label: "Awaiting your send",
          color: "var(--amber)",
          bg: "var(--amber-soft)",
        }

  const mailtoHref = running
    ? undefined
    : buildMailto({
        to: props.to,
        subject: props.subject,
        body: props.body,
        cc: props.cc,
        bcc: props.bcc,
      })

  return (
    <div
      className="lc-reveal my-1.5 mb-3.5 overflow-hidden rounded-xl"
      style={{
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div
        className="flex items-center gap-2 px-3.5 py-2.5"
        style={{
          background: "var(--bg-soft)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        {running ? (
          <Loader2
            className="lc-spin h-4 w-4"
            style={{ color: "var(--accent-ink)" }}
          />
        ) : (
          <Mail className="h-4 w-4" style={{ color: "var(--accent-ink)" }} />
        )}
        <span className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>
          Drafted
        </span>
        <code
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            color: "var(--accent-ink)",
          }}
        >
          email
        </code>
        <span
          className="rounded-md px-1.5 py-0.5"
          style={{
            fontSize: 11.5,
            color: "var(--ink-3)",
            fontFamily: "var(--font-mono)",
            background: "var(--surface)",
            border: "1px solid var(--border)",
          }}
        >
          human
        </span>
        <span
          className="ml-auto inline-flex items-center gap-1.5 rounded-full px-2 py-0.5"
          style={{
            fontSize: 11.5,
            background: pill.bg,
            border: `1px solid ${pill.color}`,
            color: pill.color,
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: pill.color }}
          />
          {pill.label}
        </span>
      </div>

      <Field label="From">
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 13,
            color: "var(--ink-2)",
          }}
        >
          {fromEmail || "—"}
        </span>
      </Field>
      <Field label="To">
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 13,
            color: "var(--ink)",
          }}
        >
          {props.to || "—"}
        </span>
        {props.cc.length > 0 && (
          <div
            className="mt-1"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12.5,
              color: "var(--ink-2)",
            }}
          >
            cc: {props.cc.join(", ")}
          </div>
        )}
        {props.bcc.length > 0 && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12.5,
              color: "var(--ink-2)",
            }}
          >
            bcc: {props.bcc.join(", ")}
          </div>
        )}
      </Field>
      <Field label="Subject">
        <span
          className="font-medium"
          style={{ fontSize: 14, color: "var(--ink)" }}
        >
          {props.subject || "—"}
        </span>
      </Field>

      {attachments.length > 0 && (
        <Field label="Attach">
          <div className="flex flex-wrap gap-1.5">
            {attachments.map((a) => (
              <AttachmentChip
                key={a.id}
                entry={a}
                onRemove={() => onRemoveAttachment(a.id)}
              />
            ))}
          </div>
        </Field>
      )}

      <div
        className="px-3.5 py-3"
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: 13.5,
          lineHeight: 1.55,
          color: "var(--ink)",
        }}
      >
        {props.body}
      </div>

      <div
        className="flex items-center justify-between gap-3 px-3.5 py-2.5"
        style={{
          borderTop: "1px solid var(--border)",
          background: "var(--bg-soft)",
        }}
      >
        <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
          {attachments.length > 0
            ? "Attachments download on Open in mail — attach them in your mail app."
            : "Sending happens in your mail app."}
        </span>
        <div className="flex items-center gap-1.5">
          <ActionBtn onClick={onCopy} disabled={running}>
            {copied ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            {copied ? "Copied" : "Copy"}
          </ActionBtn>
          <a
            href={mailtoHref}
            onClick={onOpenInMail}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12.5px]"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground, #fff)",
              border: 0,
              pointerEvents: running ? "none" : "auto",
              opacity: running ? 0.5 : 1,
            }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open in mail
          </a>
        </div>
      </div>
    </div>
  )
}

function AttachmentChip({
  entry,
  onRemove,
}: {
  entry: AttachmentEntry
  onRemove: () => void
}) {
  const label =
    entry.status === "ready"
      ? entry.artifact.title || entry.id
      : entry.status === "loading"
        ? "Loading…"
        : `Missing artifact ${entry.id.slice(0, 8)}`
  const kind = entry.status === "ready" ? entry.artifact.kind : null
  const errored = entry.status === "error"
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1"
      style={{
        background: "var(--surface)",
        border: `1px solid ${errored ? "var(--red)" : "var(--border)"}`,
        color: errored ? "var(--red)" : "var(--ink)",
        fontSize: 12.5,
      }}
    >
      {entry.status === "loading" ? (
        <Loader2
          className="lc-spin h-3.5 w-3.5"
          style={{ color: "var(--ink-3)" }}
        />
      ) : kind ? (
        <KindIcon kind={kind} />
      ) : (
        <FileText className="h-3.5 w-3.5" />
      )}
      <span
        style={{
          maxWidth: 220,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${label}`}
        className="inline-flex items-center justify-center rounded"
        style={{
          width: 16,
          height: 16,
          background: "transparent",
          border: 0,
          cursor: "pointer",
          color: "var(--ink-3)",
          padding: 0,
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div
      className="flex gap-3 px-3.5 py-2"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div
        className="w-16 shrink-0 uppercase"
        style={{
          fontSize: 11,
          color: "var(--ink-3)",
          letterSpacing: ".04em",
          paddingTop: 2,
        }}
      >
        {label}
      </div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

function ActionBtn({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12.5px]"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        color: "var(--ink)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {children}
    </button>
  )
}
