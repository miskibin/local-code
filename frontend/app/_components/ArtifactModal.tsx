"use client"

import { formatDistanceToNow } from "date-fns"
import {
  Database,
  Download,
  FileText,
  Image as ImageIcon,
  RotateCw,
  Search,
  Star,
  X,
  XIcon,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"
import type {
  Artifact,
  ArtifactTablePayload,
  ArtifactTextPayload,
} from "@/lib/types"

import { ArtifactImage } from "./ArtifactImage"
import { ArtifactSourceCode } from "./ArtifactSourceCode"
import { ArtifactTable, downloadTableCsv } from "./ArtifactTable"

function KindIcon({ kind }: { kind: Artifact["kind"] }) {
  if (kind === "table") return <Database className="h-4 w-4" />
  if (kind === "image") return <ImageIcon className="h-4 w-4" />
  return <FileText className="h-4 w-4" />
}

function UpdatedPill({ ts }: { ts?: string }) {
  if (!ts) return null
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return null
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[11px]"
      style={{ background: "var(--bg-soft)", color: "var(--ink-3)" }}
    >
      Updated {formatDistanceToNow(d, { addSuffix: true })}
    </span>
  )
}

export function ArtifactModal({
  artifact,
  saved,
  onClose,
  onRefreshed,
  onSaveArtifact,
}: {
  artifact: Artifact | null
  saved?: boolean
  onClose: () => void
  onRefreshed?: (a: Artifact) => void
  onSaveArtifact?: (a: Artifact) => void
}) {
  const [refreshing, setRefreshing] = useState(false)
  const [tableQuery, setTableQuery] = useState("")
  const open = !!artifact
  const tablePayload =
    artifact?.kind === "table"
      ? (artifact.payload as ArtifactTablePayload)
      : null
  const showTableFilter = (tablePayload?.rows?.length ?? 0) > 8

  const handleRefresh = async () => {
    if (!artifact) return
    setRefreshing(true)
    try {
      const fresh = await api.refreshArtifact(artifact.id)
      onRefreshed?.(fresh)
      toast.success("Artifact refreshed")
    } catch (e) {
      toast.error(`Refresh failed: ${(e as Error).message}`)
    } finally {
      setRefreshing(false)
    }
  }

  const canRefresh = !!artifact?.source_code && !!artifact?.source_kind

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="max-h-[90vh] w-[95vw] max-w-[1400px] overflow-hidden p-0 sm:max-w-[1400px]"
      >
        <DialogHeader
          className="flex flex-row items-center gap-3 px-5 py-3.5"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <span
            className="inline-flex shrink-0"
            style={{ color: "var(--accent)" }}
          >
            {artifact ? <KindIcon kind={artifact.kind} /> : null}
          </span>
          <DialogTitle className="min-w-0 truncate text-left text-sm font-medium">
            {artifact?.title}
          </DialogTitle>
          {showTableFilter ? (
            <div
              className="mx-auto flex items-center gap-2"
              style={{
                width: "100%",
                maxWidth: 360,
                padding: "5px 10px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--surface)",
              }}
            >
              <span
                className="inline-flex"
                style={{ color: "var(--ink-3)", flexShrink: 0 }}
              >
                <Search className="h-3.5 w-3.5" />
              </span>
              <input
                value={tableQuery}
                onChange={(e) => setTableQuery(e.target.value)}
                placeholder="Filter rows…"
                aria-label="Filter rows"
                style={{
                  flex: 1,
                  border: 0,
                  outline: 0,
                  background: "transparent",
                  fontFamily: "var(--font-sans)",
                  fontSize: 12.5,
                  color: "var(--ink)",
                  minWidth: 0,
                }}
              />
              {tableQuery ? (
                <button
                  onClick={() => setTableQuery("")}
                  title="Clear"
                  aria-label="Clear filter"
                  style={{
                    background: "transparent",
                    border: 0,
                    padding: 0,
                    color: "var(--ink-3)",
                    cursor: "pointer",
                    display: "inline-flex",
                    flexShrink: 0,
                  }}
                >
                  <X className="h-3 w-3" />
                </button>
              ) : null}
            </div>
          ) : (
            <div className="flex-1" />
          )}
          <div className="flex shrink-0 items-center gap-2">
            <UpdatedPill ts={artifact?.updated_at} />
            {tablePayload && artifact ? (
              <button
                type="button"
                onClick={() => downloadTableCsv(tablePayload, artifact.title)}
                title="Download CSV"
                aria-label="Download CSV"
                className="inline-flex size-7 items-center justify-center rounded-md transition"
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  color: "var(--ink-2)",
                  cursor: "pointer",
                }}
                data-testid="artifact-download-csv"
              >
                <Download className="h-4 w-4" />
              </button>
            ) : null}
            {artifact && onSaveArtifact ? (
              <button
                type="button"
                data-testid="artifact-save"
                disabled={!!saved}
                onClick={() => !saved && onSaveArtifact(artifact)}
                title={saved ? "Saved to artifacts" : "Save to artifacts"}
                className="inline-flex size-7 items-center justify-center rounded-md transition disabled:opacity-100"
                style={{
                  background: "transparent",
                  border: saved ? "1px solid var(--border)" : 0,
                  color: saved ? "var(--accent)" : "var(--ink-2)",
                  cursor: saved ? "default" : "pointer",
                }}
              >
                <Star className={`h-4 w-4 ${saved ? "fill-current" : ""}`} />
              </button>
            ) : null}
            {canRefresh ? (
              <button
                type="button"
                onClick={handleRefresh}
                disabled={refreshing}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition disabled:opacity-50"
                style={{
                  background: "var(--accent)",
                  color: "var(--accent-foreground)",
                  border: 0,
                  cursor: refreshing ? "default" : "pointer",
                }}
                data-testid="artifact-refresh"
                title="Re-run the source script and update the payload"
              >
                <RotateCw
                  className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
                />
                {refreshing ? "Refreshing…" : "Refresh"}
              </button>
            ) : null}
            <DialogClose asChild>
              <Button variant="ghost" size="icon-sm" title="Close">
                <XIcon />
                <span className="sr-only">Close</span>
              </Button>
            </DialogClose>
          </div>
        </DialogHeader>
        <div
          className="overflow-auto px-5 pt-3 pb-5"
          style={{ maxHeight: "calc(90vh - 60px)" }}
        >
          {artifact?.kind === "table" ? (
            <ArtifactTable
              payload={artifact.payload as ArtifactTablePayload}
              query={tableQuery}
            />
          ) : artifact?.kind === "image" ? (
            <ArtifactImage artifact={artifact} fullSize />
          ) : artifact?.kind === "text" ? (
            <pre
              className="rounded-lg p-3 whitespace-pre-wrap"
              style={{
                background: "var(--bg-soft)",
                fontFamily: "var(--font-mono)",
                fontSize: 12.5,
                color: "var(--ink-2)",
              }}
            >
              {(artifact.payload as ArtifactTextPayload).text}
            </pre>
          ) : null}
          {artifact ? (
            <ArtifactSourceCode
              sourceKind={artifact.source_kind ?? null}
              sourceCode={artifact.source_code ?? null}
            />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
