"use client"

import { Cpu, Database, Image as ImageIcon } from "lucide-react"
import { createContext, useContext, type ReactNode } from "react"
import type { Artifact } from "@/lib/types"

export type ToolArtifactRef = {
  artifactId: string
  kind: "table" | "image" | "text"
  title: string
}

export type ArtifactRefs = {
  getArtifact: (id: string) => Artifact | undefined
  getToolArtifact: (toolCallId: string) => ToolArtifactRef | undefined
  onOpen: (id: string) => void
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
