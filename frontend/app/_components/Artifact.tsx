"use client"

import {
  Check,
  Cpu,
  Database,
  Download,
  Image as ImageIcon,
  MoreHorizontal,
  Plus,
  RotateCw,
  Search,
  X,
} from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import type { Artifact as ArtifactT, ArtifactTablePayload } from "@/lib/types"
import { ArtifactTable, downloadTableCsv } from "./ArtifactTable"
import { ArtifactImage } from "./ArtifactImage"

export function ArtifactCard({
  artifact,
  saved,
  onSave,
  onOpen,
  onTableRefresh,
}: {
  artifact: ArtifactT
  saved: boolean
  onSave: (a: ArtifactT) => void
  /** Shown for non-table artifacts; opens the detail modal. */
  onOpen?: (a: ArtifactT) => void
  onTableRefresh?: (a: ArtifactT) => Promise<ArtifactT>
}) {
  const isTable = artifact.kind === "table"
  const isImage = artifact.kind === "image"
  const tablePayload = isTable
    ? (artifact.payload as ArtifactTablePayload)
    : null
  const canTableRefresh =
    isTable && !!artifact.source_code && !!artifact.source_kind
  const [tableRefreshBusy, setTableRefreshBusy] = useState(false)
  const [tableQuery, setTableQuery] = useState("")
  const showTableFilter = isTable && (tablePayload?.rows?.length ?? 0) > 8
  const meta = isTable
    ? `${tablePayload!.rows?.length ?? 0} rows · ${tablePayload!.columns?.length ?? 0} columns`
    : isImage
      ? "image · png"
      : artifact.kind
  return (
    <div
      className="lc-reveal mt-2 mb-3.5 overflow-hidden rounded-xl"
      style={{
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div
        className="flex items-center gap-2.5 px-3.5 py-2.5"
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-soft)",
        }}
      >
        <span className="inline-flex" style={{ color: "var(--accent)" }}>
          {isTable ? (
            <Database className="h-3.5 w-3.5" />
          ) : isImage ? (
            <ImageIcon className="h-3.5 w-3.5" />
          ) : (
            <Cpu className="h-3.5 w-3.5" />
          )}
        </span>
        <div className="flex min-w-0 flex-col">
          <div
            className="text-[13px] font-medium"
            style={{ color: "var(--ink)" }}
          >
            {artifact.title}
          </div>
          <div
            className="mt-0.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11.5,
              color: "var(--ink-3)",
            }}
          >
            {meta}
          </div>
        </div>
        {showTableFilter ? (
          <div
            className="mx-auto flex items-center gap-2"
            style={{
              width: "100%",
              maxWidth: 320,
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
        {!isTable && onOpen ? (
          <button
            onClick={() => onOpen(artifact)}
            title="Open"
            className="rounded-md p-1.5 transition"
            style={{ background: "transparent", color: "var(--ink-2)" }}
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        ) : null}
        {isTable && tablePayload ? (
          <button
            type="button"
            onClick={() => downloadTableCsv(tablePayload, artifact.title)}
            title="Download CSV"
            aria-label="Download CSV"
            className="inline-flex items-center justify-center rounded-md p-1.5 transition"
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--ink-2)",
              cursor: "pointer",
            }}
            data-testid="artifact-table-download-csv"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
        ) : null}
        {isTable && canTableRefresh && onTableRefresh ? (
          <button
            type="button"
            onClick={async () => {
              setTableRefreshBusy(true)
              try {
                await onTableRefresh(artifact)
                toast.success("Artifact refreshed")
              } catch (e) {
                toast.error(`Refresh failed: ${(e as Error).message}`)
              } finally {
                setTableRefreshBusy(false)
              }
            }}
            disabled={tableRefreshBusy}
            title="Re-run the source script and update the payload"
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition disabled:opacity-50"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground)",
              border: 0,
              cursor: tableRefreshBusy ? "default" : "pointer",
            }}
            data-testid="artifact-table-inline-refresh"
          >
            <RotateCw
              className={`h-3.5 w-3.5 ${tableRefreshBusy ? "animate-spin" : ""}`}
            />
            {tableRefreshBusy ? "…" : "Refresh"}
          </button>
        ) : null}
        <button
          onClick={() => onSave(artifact)}
          disabled={saved}
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
      </div>
      {isTable ? (
        <ArtifactTable payload={tablePayload!} query={tableQuery} />
      ) : isImage ? (
        <ArtifactImage artifact={artifact} />
      ) : null}
    </div>
  )
}
