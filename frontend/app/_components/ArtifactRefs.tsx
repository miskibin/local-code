"use client"

import {
  Check,
  Cpu,
  Database,
  Image as ImageIcon,
  Plus,
  RotateCw,
} from "lucide-react"
import { createContext, useContext, useState, type ReactNode } from "react"
import { toast } from "sonner"
import type { Artifact, ArtifactImagePayload } from "@/lib/types"

import { ARTIFACT_IMAGE_PREVIEW_MAX_PX } from "./ArtifactImage"
import { ArtifactCard } from "./Artifact"

export type ToolArtifactRef = {
  artifactId: string
  kind: "table" | "image" | "text"
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
  kind?: "table" | "image" | "text"
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
        : Cpu
  const onClick = () => refs?.onOpen(id)
  return (
    <button
      type="button"
      onClick={onClick}
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
    </button>
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
            title="Re-run and refresh"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 28,
              height: 28,
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: "transparent",
              color: "var(--ink-2)",
              cursor: refreshing ? "default" : "pointer",
              opacity: refreshing ? 0.5 : 1,
            }}
          >
            <RotateCw
              className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
            />
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
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 28,
              height: 28,
              borderRadius: 6,
              border: "1px solid var(--border)",
              background: saved ? "transparent" : "var(--accent)",
              color: saved ? "var(--ink-2)" : "var(--accent-foreground)",
              cursor: saved ? "default" : "pointer",
            }}
          >
            {saved ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
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
  return <ArtifactChip id={id} />
}
