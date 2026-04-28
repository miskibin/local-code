"use client"

import { Check, Copy, ExternalLink, Loader2, Mail, Trash2 } from "lucide-react"
import { useState } from "react"

export type EmailDraftCardProps = {
  toolCallId: string
  to: string
  subject: string
  body: string
  from: string
  cc: string[]
  bcc: string[]
  status: "running" | "done" | "error"
}

function buildMailto(p: EmailDraftCardProps): string {
  const params = new URLSearchParams()
  if (p.subject) params.set("subject", p.subject)
  if (p.body) params.set("body", p.body)
  if (p.cc.length) params.set("cc", p.cc.join(","))
  if (p.bcc.length) params.set("bcc", p.bcc.join(","))
  const qs = params.toString()
  return `mailto:${encodeURIComponent(p.to)}${qs ? `?${qs}` : ""}`
}

function buildPlainText(p: EmailDraftCardProps): string {
  const lines: string[] = []
  if (p.from) lines.push(`From: ${p.from}`)
  lines.push(`To: ${p.to}`)
  if (p.cc.length) lines.push(`Cc: ${p.cc.join(", ")}`)
  if (p.bcc.length) lines.push(`Bcc: ${p.bcc.join(", ")}`)
  lines.push(`Subject: ${p.subject}`)
  lines.push("")
  lines.push(p.body)
  return lines.join("\n")
}

type LocalState = "draft" | "sent" | "discarded"

export function EmailDraftCard(props: EmailDraftCardProps) {
  const [state, setState] = useState<LocalState>("draft")
  const [copied, setCopied] = useState(false)
  const running = props.status === "running"
  const errored = props.status === "error"

  const onCopy = async () => {
    await navigator.clipboard.writeText(buildPlainText(props))
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const pill = errored
    ? { label: "Drafting failed", color: "var(--red)", bg: "var(--red-soft)" }
    : running
      ? { label: "Drafting…", color: "var(--accent)", bg: "var(--accent-soft)" }
      : state === "sent"
        ? { label: "Marked sent", color: "var(--accent)", bg: "var(--accent-soft)" }
        : state === "discarded"
          ? { label: "Discarded", color: "var(--ink-3)", bg: "var(--bg-soft)" }
          : { label: "Awaiting your send", color: "var(--amber)", bg: "var(--amber-soft)" }

  return (
    <div
      className="lc-reveal my-1.5 mb-3.5 overflow-hidden rounded-xl"
      style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <div
        className="flex items-center gap-2 px-3.5 py-2.5"
        style={{ background: "var(--bg-soft)", borderBottom: "1px solid var(--border)" }}
      >
        {running ? (
          <Loader2 className="lc-spin h-4 w-4" style={{ color: "var(--accent-ink)" }} />
        ) : (
          <Mail className="h-4 w-4" style={{ color: "var(--accent-ink)" }} />
        )}
        <span className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>
          Drafted
        </span>
        <code
          style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--accent-ink)" }}
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
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: pill.color }} />
          {pill.label}
        </span>
      </div>

      <Field label="From">
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-2)" }}>
          {props.from || "—"}
        </span>
      </Field>
      <Field label="To">
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink)" }}>
          {props.to || "—"}
        </span>
        {props.cc.length > 0 && (
          <div
            className="mt-1"
            style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--ink-2)" }}
          >
            cc: {props.cc.join(", ")}
          </div>
        )}
        {props.bcc.length > 0 && (
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--ink-2)" }}>
            bcc: {props.bcc.join(", ")}
          </div>
        )}
      </Field>
      <Field label="Subject">
        <span className="font-medium" style={{ fontSize: 14, color: "var(--ink)" }}>
          {props.subject || "—"}
        </span>
      </Field>

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
        style={{ borderTop: "1px solid var(--border)", background: "var(--bg-soft)" }}
      >
        <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
          Sending happens in your mail app.
        </span>
        <div className="flex items-center gap-1.5">
          <ActionBtn onClick={onCopy} disabled={running || state === "discarded"}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </ActionBtn>
          <ActionBtn onClick={() => setState("discarded")} disabled={running || state !== "draft"}>
            <Trash2 className="h-3.5 w-3.5" />
            Discard
          </ActionBtn>
          <ActionBtn onClick={() => setState("sent")} disabled={running || state !== "draft"}>
            <Check className="h-3.5 w-3.5" />
            Mark sent
          </ActionBtn>
          <a
            href={running ? undefined : buildMailto(props)}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12.5px]"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground, #fff)",
              border: 0,
              pointerEvents: running || state === "discarded" ? "none" : "auto",
              opacity: running || state === "discarded" ? 0.5 : 1,
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 px-3.5 py-2" style={{ borderBottom: "1px solid var(--border)" }}>
      <div
        className="w-16 shrink-0 uppercase"
        style={{ fontSize: 11, color: "var(--ink-3)", letterSpacing: ".04em", paddingTop: 2 }}
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
