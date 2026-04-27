"use client"

import type { ArtifactColumn, ArtifactTablePayload } from "@/lib/types"

function formatCell(v: unknown, c: ArtifactColumn): string {
  if (v == null) return "—"
  if (c.numeric && typeof v === "number") {
    return c.format === "currency"
      ? "$" + v.toLocaleString()
      : v.toLocaleString()
  }
  return String(v)
}

export function ArtifactTable({ payload }: { payload: ArtifactTablePayload }) {
  const { columns, rows } = payload
  return (
    <div className="lc-scroll" style={{ maxHeight: 280, overflow: "auto" }}>
      <table
        className="w-full border-collapse"
        style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
      >
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className="px-3 py-2 whitespace-nowrap"
                style={{
                  position: "sticky",
                  top: 0,
                  background: "var(--surface)",
                  borderBottom: "1px solid var(--border)",
                  textAlign: c.numeric ? "right" : "left",
                  color: "var(--ink-2)",
                  fontWeight: 500,
                }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  className="px-3 py-1.5 whitespace-nowrap"
                  style={{
                    textAlign: c.numeric ? "right" : "left",
                    color: "var(--ink)",
                  }}
                >
                  {formatCell(r[c.key], c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
