"use client";

import { Check, Copy, ExternalLink, Mail, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type { ToolResultProps, ToolRenderer } from "./types";
import { DefaultResult } from "./default";

type Draft = {
  to: string;
  subject: string;
  body: string;
  from: string;
  cc: string[];
  bcc: string[];
};

function parseDraft(result: string): Draft | null {
  if (!result) return null;
  try {
    const obj = JSON.parse(result) as Partial<Draft>;
    if (typeof obj?.to !== "string" || typeof obj?.subject !== "string" || typeof obj?.body !== "string") {
      return null;
    }
    return {
      to: obj.to,
      subject: obj.subject,
      body: obj.body,
      from: typeof obj.from === "string" ? obj.from : "",
      cc: Array.isArray(obj.cc) ? obj.cc.filter((s): s is string => typeof s === "string") : [],
      bcc: Array.isArray(obj.bcc) ? obj.bcc.filter((s): s is string => typeof s === "string") : [],
    };
  } catch {
    return null;
  }
}

function buildMailto(d: Draft): string {
  const params = new URLSearchParams();
  if (d.subject) params.set("subject", d.subject);
  if (d.body) params.set("body", d.body);
  if (d.cc.length) params.set("cc", d.cc.join(","));
  if (d.bcc.length) params.set("bcc", d.bcc.join(","));
  const qs = params.toString();
  return `mailto:${encodeURIComponent(d.to)}${qs ? `?${qs}` : ""}`;
}

function buildPlainText(d: Draft): string {
  const lines: string[] = [];
  if (d.from) lines.push(`From: ${d.from}`);
  lines.push(`To: ${d.to}`);
  if (d.cc.length) lines.push(`Cc: ${d.cc.join(", ")}`);
  if (d.bcc.length) lines.push(`Bcc: ${d.bcc.join(", ")}`);
  lines.push(`Subject: ${d.subject}`);
  lines.push("");
  lines.push(d.body);
  return lines.join("\n");
}

type LocalState = "draft" | "sent" | "discarded";

function EmailDraftResult({ result, status, step }: ToolResultProps) {
  const draft = useMemo(() => parseDraft(result), [result]);
  const [state, setState] = useState<LocalState>("draft");
  const [copied, setCopied] = useState(false);

  if (!draft) return <DefaultResult result={result} status={status} step={step} />;

  const onCopy = async () => {
    await navigator.clipboard.writeText(buildPlainText(draft));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const pill =
    state === "sent"
      ? { label: "Marked sent", color: "var(--accent)", bg: "var(--accent-soft)" }
      : state === "discarded"
        ? { label: "Discarded", color: "var(--ink-3)", bg: "var(--bg-soft)" }
        : { label: "Awaiting your send", color: "var(--amber)", bg: "var(--amber-soft)" };

  return (
    <div
      className="overflow-hidden rounded-lg"
      style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2"
        style={{
          background: "var(--bg-soft)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <Mail className="h-4 w-4" style={{ color: "var(--accent-ink)" }} />
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
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: pill.color }} />
          {pill.label}
        </span>
      </div>

      <Field label="From">
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-2)" }}>
          {draft.from || "—"}
        </span>
      </Field>
      <Field label="To">
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink)" }}>
          {draft.to}
        </span>
        {draft.cc.length > 0 && (
          <div className="mt-1" style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--ink-2)" }}>
            cc: {draft.cc.join(", ")}
          </div>
        )}
        {draft.bcc.length > 0 && (
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--ink-2)" }}>
            bcc: {draft.bcc.join(", ")}
          </div>
        )}
      </Field>
      <Field label="Subject">
        <span className="font-medium" style={{ fontSize: 14, color: "var(--ink)" }}>
          {draft.subject}
        </span>
      </Field>

      <div
        className="px-3 py-3"
        style={{
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: 13.5,
          lineHeight: 1.55,
          color: "var(--ink)",
        }}
      >
        {draft.body}
      </div>

      <div
        className="flex items-center justify-between gap-3 px-3 py-2"
        style={{ borderTop: "1px solid var(--border)", background: "var(--bg-soft)" }}
      >
        <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
          Sending happens in your mail app.
        </span>
        <div className="flex items-center gap-1.5">
          <ActionBtn onClick={onCopy} disabled={state === "discarded"}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </ActionBtn>
          <ActionBtn onClick={() => setState("discarded")} disabled={state !== "draft"}>
            <Trash2 className="h-3.5 w-3.5" />
            Discard
          </ActionBtn>
          <ActionBtn onClick={() => setState("sent")} disabled={state !== "draft"}>
            <Check className="h-3.5 w-3.5" />
            Mark sent
          </ActionBtn>
          <a
            href={buildMailto(draft)}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12.5px]"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground, #fff)",
              border: 0,
              pointerEvents: state === "discarded" ? "none" : "auto",
              opacity: state === "discarded" ? 0.5 : 1,
            }}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open in mail
          </a>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      className="flex gap-3 px-3 py-2"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div
        className="w-16 shrink-0 uppercase"
        style={{ fontSize: 11, color: "var(--ink-3)", letterSpacing: ".04em", paddingTop: 2 }}
      >
        {label}
      </div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function ActionBtn({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
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
  );
}

export const emailDraftRenderer: ToolRenderer = {
  hideArgs: true,
  getHeaderLabel: (step) => {
    const subject =
      typeof step.args?.subject === "string" && step.args.subject.length > 0
        ? (step.args.subject as string)
        : "email";
    const truncated = subject.length > 60 ? subject.slice(0, 60) + "…" : subject;
    return (
      <>
        <span style={{ color: "var(--ink-2)" }}>Drafted</span>
        <span style={{ color: "var(--ink)", fontWeight: 500 }}>{truncated}</span>
      </>
    );
  },
  Result: EmailDraftResult,
};
