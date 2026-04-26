"use client";

import {
  ArrowUp,
  Database,
  FileText,
  ImageIcon,
  Paperclip,
  Square,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Artifact } from "@/lib/types";
import { ModelPicker } from "./ModelPicker";

type Props = {
  onSend: (text: string, attachments: Artifact[]) => void;
  onStop?: () => void;
  streaming: boolean;
  model?: string;
  onModelChange?: (m: string) => void;
  sessionId: string;
  onAttachmentUploaded?: (a: Artifact) => void;
};

export function Composer({
  onSend,
  onStop,
  streaming,
  model,
  onModelChange,
  sessionId,
  onAttachmentUploaded,
}: Props) {
  const [text, setText] = useState("");
  const [pending, setPending] = useState<Artifact[]>([]);
  const [uploading, setUploading] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const capped = ta.scrollHeight > 200;
    ta.style.height = (capped ? 200 : ta.scrollHeight) + "px";
    ta.style.overflowY = capped ? "auto" : "hidden";
  }, [text]);

  const upload = async (files: File[] | FileList | null) => {
    if (!files) return;
    const list = Array.from(files);
    if (list.length === 0) return;
    setUploading((n) => n + list.length);
    try {
      const uploaded = await Promise.all(
        list.map((f) =>
          api.uploadArtifact(f, sessionId).catch((e) => {
            toast.error("Upload failed", {
              description: e instanceof Error ? e.message : String(e),
            });
            return null;
          }),
        ),
      );
      const ok = uploaded.filter((a): a is Artifact => !!a);
      setPending((p) => [...p, ...ok]);
      for (const a of ok) onAttachmentUploaded?.(a);
    } finally {
      setUploading((n) => n - list.length);
    }
  };

  const submit = () => {
    const t = text.trim();
    if ((!t && pending.length === 0) || streaming || uploading > 0) return;
    onSend(t, pending);
    setText("");
    setPending([]);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (!e.clipboardData?.files?.length) return;
    e.preventDefault();
    void upload(e.clipboardData.files);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer?.files?.length) void upload(e.dataTransfer.files);
  };

  const removeAttachment = (id: string) =>
    setPending((p) => p.filter((a) => a.id !== id));

  const canSend = (text.trim().length > 0 || pending.length > 0) && !streaming && uploading === 0;

  return (
    <div className="mx-auto w-full max-w-5xl px-8 pb-4 pt-1">
      <div
        className="rounded-3xl px-3.5 pt-2.5 pb-2 transition"
        style={{
          background: "#fff",
          border: dragOver ? "1px solid var(--accent)" : "1px solid var(--border)",
          boxShadow: dragOver
            ? "0 0 0 3px var(--accent-soft)"
            : "0 1px 0 rgba(0,0,0,.02)",
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (e.dataTransfer?.types?.includes("Files")) setDragOver(true);
        }}
        onDragLeave={(e) => {
          if (e.currentTarget.contains(e.relatedTarget as Node)) return;
          setDragOver(false);
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
            void upload(e.target.files);
            e.target.value = "";
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
                style={{
                  background: "var(--ink)",
                  border: 0,
                  cursor: "pointer",
                }}
              >
                <Square className="h-3 w-3" />
              </button>
            ) : (
              <button
                onClick={submit}
                disabled={!canSend}
                title="Send"
                className="grid h-8 w-8 place-items-center rounded-full text-white transition"
                style={{
                  background: canSend ? "var(--accent)" : "var(--hover-strong)",
                  border: 0,
                  cursor: canSend ? "pointer" : "not-allowed",
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

function AttachmentChip({
  artifact,
  onRemove,
}: {
  artifact: Artifact;
  onRemove: () => void;
}) {
  const Icon =
    artifact.kind === "image"
      ? ImageIcon
      : artifact.kind === "table"
        ? Database
        : FileText;
  const subtitle = artifact.summary || artifact.kind;
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
