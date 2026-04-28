"use client"

import {
  Check,
  Cpu,
  Database,
  Download,
  FileText,
  Image as ImageIcon,
  Plus,
  RotateCw,
} from "lucide-react"
import { createContext, useContext, useState, type ReactNode } from "react"
import { toast } from "sonner"
import { BACKEND_URL } from "@/lib/api"
import type { Artifact, ArtifactImagePayload } from "@/lib/types"

import {
  ARTIFACT_IMAGE_PREVIEW_MAX_PX,
  downloadImagePng,
} from "./ArtifactImage"
import { ArtifactCard } from "./Artifact"

export type ToolArtifactRef = {
  artifactId: string
  kind: "table" | "image" | "text" | "pptx"
  title: string
}

export type ArtifactRefs = {
  getArtifact: (id: string) => Artifact | undefined
  getToolArtifact: (toolCallId: string) => ToolArtifactRef | undefined
  onOpen: (id: string) => void
  isSaved?: (id: string) => boolean
  onSave?: (artifact: Artifact) => void
  /** Re-run source and return fresh artifact; updates cache in ChatView. */
  onTableRefresh?: (artifact: Artifact) => Promise<Artifact>
}

const Ctx = createContext<ArtifactRefs | null>(null)

export const ArtifactRefsProvider = Ctx.Provider

export function useArtifactRefs(): ArtifactRefs | null {
  return useContext(Ctx)
}

export function ArtifactChip({
  id,
  title,
  kind,
  label,
}: {
  id: string
  title?: string
  kind?: "table" | "image" | "text" | "pptx"
  label?: ReactNode
}) {
  const refs = useArtifactRefs()
  const fromCtx = refs?.getArtifact(id)
  const resolvedTitle = title ?? fromCtx?.title ?? id
  const resolvedKind = kind ?? fromCtx?.kind
  const Icon =
    resolvedKind === "table"
      ? Database
      : resolvedKind === "image"
        ? ImageIcon
        : resolvedKind === "pptx"
          ? FileText
          : Cpu
  const onClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    refs?.onOpen(id)
  }
  // role=button instead of <button> so the chip can sit inside a parent
  // <button> (e.g. ToolCall's collapse toggle) without invalid HTML nesting.
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          e.stopPropagation()
          refs?.onOpen(id)
        }
      }}
      title={resolvedTitle}
      className="inline-flex max-w-[260px] items-center gap-1.5 rounded-md px-2 py-0.5 align-baseline text-[12px]"
      style={{
        background: "var(--accent-soft)",
        border: "1px solid var(--border)",
        color: "var(--accent-ink)",
        cursor: refs ? "pointer" : "default",
      }}
    >
      <Icon
        className="h-3 w-3 flex-shrink-0"
        style={{ color: "var(--accent)" }}
      />
      <span className="truncate">{label ?? resolvedTitle}</span>
    </span>
  )
}

function InlineArtifactImage({
  id,
  artifact,
  refs,
}: {
  id: string
  artifact: Artifact
  refs: ArtifactRefs | null
}) {
  const [refreshing, setRefreshing] = useState(false)
  const payload = artifact.payload as ArtifactImagePayload
  if (!payload?.data_b64) return <ArtifactChip id={id} />
  const src = `data:image/${payload.format};base64,${payload.data_b64}`
  const saved = refs?.isSaved?.(id) ?? false
  const canRefresh = !!artifact.source_code && !!artifact.source_kind

  return (
    <span
      style={{
        display: "block",
        margin: "0.5rem 0",
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <span
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 14px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-soft)",
        }}
      >
        <span className="inline-flex" style={{ color: "var(--accent)" }}>
          <ImageIcon className="h-3.5 w-3.5" />
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "var(--ink)",
            flex: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {artifact.title}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            downloadImagePng(payload, artifact.title)
          }}
          title="Download PNG"
          aria-label="Download PNG"
          className="inline-flex items-center justify-center rounded-md p-1.5 transition"
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--ink-2)",
            cursor: "pointer",
          }}
          data-testid="artifact-image-download-png"
        >
          <Download className="h-3.5 w-3.5" />
        </button>
        {canRefresh && refs?.onTableRefresh ? (
          <button
            type="button"
            onClick={async (e) => {
              e.stopPropagation()
              setRefreshing(true)
              try {
                await refs.onTableRefresh!(artifact)
                toast.success("Artifact refreshed")
              } catch (err) {
                toast.error(`Refresh failed: ${(err as Error).message}`)
              } finally {
                setRefreshing(false)
              }
            }}
            disabled={refreshing}
            title="Re-run the source script and update the payload"
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition disabled:opacity-50"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground)",
              border: 0,
              cursor: refreshing ? "default" : "pointer",
            }}
            data-testid="artifact-image-inline-refresh"
          >
            <RotateCw
              className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
            />
            {refreshing ? "…" : "Refresh"}
          </button>
        ) : null}
        {refs?.onSave ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              if (!saved) refs.onSave!(artifact)
            }}
            disabled={saved}
            title={saved ? "Saved" : "Save artifact"}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 transition"
            style={{
              background: saved ? "transparent" : "var(--accent)",
              color: saved ? "var(--ink-2)" : "var(--accent-foreground)",
              fontSize: 12,
              fontWeight: 500,
              border: saved ? "1px solid var(--border)" : 0,
              cursor: saved ? "default" : "pointer",
            }}
          >
            {saved ? (
              <>
                <Check className="h-3 w-3" /> Saved
              </>
            ) : (
              <>
                <Plus className="h-3 w-3" /> Save
              </>
            )}
          </button>
        ) : null}
      </span>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={artifact.title}
        onClick={() => refs?.onOpen(id)}
        role={refs ? "button" : undefined}
        style={{
          display: "block",
          margin: "0 auto",
          width: "auto",
          maxWidth: "100%",
          maxHeight: ARTIFACT_IMAGE_PREVIEW_MAX_PX,
          objectFit: "contain",
          cursor: refs ? "zoom-in" : "default",
        }}
      />
      {payload.caption ? (
        <span
          style={{
            display: "block",
            padding: "6px 12px",
            fontSize: 11.5,
            color: "var(--ink-3)",
            textAlign: "center",
            borderTop: "1px solid var(--border)",
            background: "var(--bg-soft)",
          }}
        >
          {payload.caption}
        </span>
      ) : null}
    </span>
  )
}

function InlineArtifactPptx({
  id,
  artifact,
  refs,
}: {
  id: string
  artifact: Artifact
  refs: ArtifactRefs | null
}) {
  const payload = artifact.payload as {
    filename?: string
    slide_count?: number
    size_bytes?: number
  }
  const slides = payload?.slide_count
  const sizeKb =
    typeof payload?.size_bytes === "number"
      ? Math.round(payload.size_bytes / 1024)
      : null
  const saved = refs?.isSaved?.(id) ?? false
  const onClickBody = (e: React.MouseEvent) => {
    e.stopPropagation()
    refs?.onOpen(id)
  }

  return (
    <span
      style={{
        display: "block",
        margin: "0.5rem 0",
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <span
        role={refs ? "button" : undefined}
        tabIndex={refs ? 0 : -1}
        onClick={onClickBody}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            e.stopPropagation()
            refs?.onOpen(id)
          }
        }}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "12px 14px",
          background: "var(--bg-soft)",
          cursor: refs ? "pointer" : "default",
        }}
      >
        <span
          className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md"
          style={{
            background: "var(--accent-soft)",
            color: "var(--accent)",
          }}
        >
          <FileText className="h-5 w-5" />
        </span>
        <span
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            minWidth: 0,
          }}
        >
          <span
            style={{
              fontSize: 13.5,
              fontWeight: 600,
              color: "var(--ink)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {artifact.title}
          </span>
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
            {slides != null ? `${slides} slides` : "Presentation"}
            {sizeKb != null ? ` · ${sizeKb} KB` : ""}
            {" · .pptx"}
          </span>
        </span>
        <a
          href={`${BACKEND_URL}/artifacts/${id}/file`}
          download
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
          title="Download .pptx"
          aria-label="Download .pptx"
          className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-[12px] font-medium transition"
          style={{
            background: "var(--accent)",
            color: "var(--accent-foreground, #fff)",
            border: 0,
          }}
        >
          <Download className="h-3.5 w-3.5" />
          Download
        </a>
        {refs?.onSave ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              if (!saved) refs.onSave!(artifact)
            }}
            disabled={saved}
            title={saved ? "Saved" : "Save artifact"}
            className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium transition"
            style={{
              background: saved ? "transparent" : "var(--bg-soft)",
              color: saved ? "var(--ink-2)" : "var(--ink)",
              border: "1px solid var(--border)",
              cursor: saved ? "default" : "pointer",
            }}
          >
            {saved ? (
              <>
                <Check className="h-3 w-3" /> Saved
              </>
            ) : (
              <>
                <Plus className="h-3 w-3" /> Save
              </>
            )}
          </button>
        ) : null}
      </span>
    </span>
  )
}

export function InlineArtifact({ id }: { id: string }) {
  const refs = useArtifactRefs()
  const artifact = refs?.getArtifact(id)
  if (!artifact) return <ArtifactChip id={id} />
  if (artifact.kind === "image") {
    return <InlineArtifactImage id={id} artifact={artifact} refs={refs} />
  }
  if (artifact.kind === "table") {
    const saved = refs?.isSaved?.(id) ?? false
    const onSave = refs?.onSave ?? (() => {})
    return (
      <span style={{ display: "block" }}>
        <ArtifactCard
          artifact={artifact}
          saved={saved}
          onSave={onSave}
          onTableRefresh={refs?.onTableRefresh}
        />
      </span>
    )
  }
  if (artifact.kind === "pptx") {
    return <InlineArtifactPptx id={id} artifact={artifact} refs={refs} />
  }
  return <ArtifactChip id={id} />
}
