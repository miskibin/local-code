"use client"

import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import { useEffect, useMemo, useState, type ReactNode } from "react"

import type { ArtifactColumn, ArtifactTablePayload } from "@/lib/types"

const PAGE_SIZE = 10

type SortDir = "asc" | "desc"

function formatCell(v: unknown, c: ArtifactColumn): string {
  if (v == null) return "—"
  if (c.numeric && typeof v === "number") {
    return c.format === "currency"
      ? "$" + v.toLocaleString()
      : v.toLocaleString()
  }
  return String(v)
}

function csvCell(v: unknown): string {
  if (v == null) return ""
  const s = String(v)
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function tableToCsv(payload: ArtifactTablePayload): string {
  const { columns, rows } = payload
  const header = columns.map((c) => csvCell(c.label ?? c.key)).join(",")
  const body = rows
    .map((r) => columns.map((c) => csvCell(r[c.key])).join(","))
    .join("\n")
  return body ? `${header}\n${body}` : header
}

export function downloadTableCsv(
  payload: ArtifactTablePayload,
  filename: string
): void {
  const safe =
    (filename || "table").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 120) + ".csv"
  const blob = new Blob([`﻿${tableToCsv(payload)}`], {
    type: "text/csv;charset=utf-8",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = safe
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function compare(a: unknown, b: unknown, numeric: boolean | undefined): number {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (numeric) {
    const an = typeof a === "number" ? a : Number(a)
    const bn = typeof b === "number" ? b : Number(b)
    if (!Number.isNaN(an) && !Number.isNaN(bn)) return an - bn
  }
  return String(a).localeCompare(String(b))
}

export function ArtifactTable({
  payload,
  query = "",
}: {
  payload: ArtifactTablePayload
  query?: string
}) {
  const { columns, rows } = payload
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [page, setPage] = useState(0)

  const q = query.trim().toLowerCase()

  const filtered = useMemo(() => {
    if (!q) return rows
    return rows.filter((r) =>
      columns.some((c) => {
        const v = r[c.key]
        return v != null && String(v).toLowerCase().includes(q)
      })
    )
  }, [rows, columns, q])

  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    const col = columns.find((c) => c.key === sortKey)
    if (!col) return filtered
    const out = [...filtered].sort((a, b) =>
      compare(a[sortKey], b[sortKey], col.numeric)
    )
    return sortDir === "desc" ? out.reverse() : out
  }, [filtered, sortKey, sortDir, columns])

  useEffect(() => {
    setPage(0)
  }, [q, sortKey, sortDir])

  const total = sorted.length
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const safePage = Math.min(page, pageCount - 1)
  const start = safePage * PAGE_SIZE
  const pageRows = sorted.slice(start, start + PAGE_SIZE)

  const onSort = (key: string) => {
    if (sortKey !== key) {
      setSortKey(key)
      setSortDir("asc")
      return
    }
    if (sortDir === "asc") {
      setSortDir("desc")
      return
    }
    setSortKey(null)
    setSortDir("asc")
  }

  const showPager = total > PAGE_SIZE

  return (
    <div>
      <div className="lc-scroll" style={{ maxHeight: 320, overflow: "auto" }}>
        <table
          className="w-full border-collapse"
          style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
        >
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sortKey === c.key
                return (
                  <th
                    key={c.key}
                    style={{
                      position: "sticky",
                      top: 0,
                      zIndex: 1,
                      background: "var(--surface)",
                      borderBottom: "1px solid var(--border)",
                      padding: 0,
                      textAlign: c.numeric ? "right" : "left",
                      color: active ? "var(--accent)" : "var(--ink-2)",
                      fontWeight: 500,
                      whiteSpace: "nowrap",
                    }}
                    aria-sort={
                      active
                        ? sortDir === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                  >
                    <button
                      onClick={() => onSort(c.key)}
                      className="inline-flex items-center gap-1 transition-colors"
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        justifyContent: c.numeric ? "flex-end" : "flex-start",
                        background: "transparent",
                        border: 0,
                        font: "inherit",
                        color: "inherit",
                        cursor: "pointer",
                        textAlign: c.numeric ? "right" : "left",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "var(--bg-soft)"
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent"
                      }}
                    >
                      <span>{c.label}</span>
                      <SortGlyph active={active} dir={sortDir} />
                    </button>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{
                    padding: "32px 14px",
                    textAlign: "center",
                    color: "var(--ink-3)",
                    fontFamily: "var(--font-sans)",
                    fontSize: 13,
                  }}
                >
                  No results.
                </td>
              </tr>
            ) : (
              pageRows.map((r, i) => (
                <tr
                  key={start + i}
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      style={{
                        padding: "7px 12px",
                        textAlign: c.numeric ? "right" : "left",
                        color: "var(--ink)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatCell(r[c.key], c)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showPager ? (
        <div
          className="flex items-center gap-2.5"
          style={{
            padding: "8px 14px",
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
            fontFamily: "var(--font-mono)",
            fontSize: 11.5,
            color: "var(--ink-3)",
          }}
        >
          <div>
            {total === 0
              ? "0"
              : `${start + 1}–${Math.min(start + PAGE_SIZE, total)}`}{" "}
            of {total}
          </div>
          <div
            className="flex items-center gap-1"
            style={{ marginLeft: "auto" }}
          >
            <span style={{ marginRight: 8 }}>
              Page {safePage + 1} / {pageCount}
            </span>
            <PagerBtn
              disabled={safePage === 0}
              onClick={() => setPage(0)}
              title="First page"
            >
              <ChevronsLeft className="h-3.5 w-3.5" />
            </PagerBtn>
            <PagerBtn
              disabled={safePage === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              title="Previous"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </PagerBtn>
            <PagerBtn
              disabled={safePage >= pageCount - 1}
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              title="Next"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </PagerBtn>
            <PagerBtn
              disabled={safePage >= pageCount - 1}
              onClick={() => setPage(pageCount - 1)}
              title="Last page"
            >
              <ChevronsRight className="h-3.5 w-3.5" />
            </PagerBtn>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function SortGlyph({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) {
    return (
      <svg
        width="9"
        height="11"
        viewBox="0 0 9 11"
        style={{ flexShrink: 0, opacity: 0.55 }}
      >
        <path d="M4.5 1 L7.5 4 L1.5 4 Z" fill="currentColor" opacity=".5" />
        <path d="M4.5 10 L7.5 7 L1.5 7 Z" fill="currentColor" opacity=".5" />
      </svg>
    )
  }
  return (
    <svg width="9" height="11" viewBox="0 0 9 11" style={{ flexShrink: 0 }}>
      {dir === "asc" ? (
        <path d="M4.5 2 L8 7 L1 7 Z" fill="currentColor" />
      ) : (
        <path d="M4.5 9 L8 4 L1 4 Z" fill="currentColor" />
      )}
    </svg>
  )
}

function PagerBtn({
  children,
  disabled,
  onClick,
  title,
}: {
  children: ReactNode
  disabled: boolean
  onClick: () => void
  title: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={title}
      className="inline-flex items-center justify-center transition-colors"
      style={{
        width: 24,
        height: 24,
        borderRadius: 6,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        color: disabled ? "var(--ink-4)" : "var(--ink-2)",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.55 : 1,
      }}
      onMouseEnter={(e) => {
        if (!disabled) e.currentTarget.style.background = "var(--bg-soft)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "var(--surface)"
      }}
    >
      {children}
    </button>
  )
}
