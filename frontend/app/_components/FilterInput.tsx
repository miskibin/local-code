"use client"

import { Search, X } from "lucide-react"

export function FilterInput({
  value,
  onChange,
  placeholder = "Filter rows…",
  ariaLabel = "Filter rows",
  maxWidth = 320,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  ariaLabel?: string
  maxWidth?: number
}) {
  return (
    <div
      className="mx-auto flex items-center gap-2"
      style={{
        width: "100%",
        maxWidth,
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
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
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
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
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
  )
}
