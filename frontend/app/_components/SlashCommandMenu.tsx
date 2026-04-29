"use client"

import { useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api"

export type SlashCommand = {
  name: string
  description: string
  arg_hint: string
}

let _cache: Promise<SlashCommand[]> | null = null

export function loadCommands(): Promise<SlashCommand[]> {
  if (!_cache) {
    _cache = api.listCommands().catch(() => {
      _cache = null
      return []
    })
  }
  return _cache
}

export function parseSlashQuery(text: string): string | null {
  if (!text.startsWith("/")) return null
  const nl = text.indexOf("\n")
  if (nl >= 0) return null
  if (text.indexOf(" ") >= 0) return null
  return text.slice(1)
}

type Props = {
  query: string
  selectedIndex: number
  onHover: (index: number) => void
  onSelect: (cmd: SlashCommand) => void
  onMatchesChange: (matches: SlashCommand[]) => void
}

export function SlashCommandMenu({
  query,
  selectedIndex,
  onHover,
  onSelect,
  onMatchesChange,
}: Props) {
  const [commands, setCommands] = useState<SlashCommand[]>([])

  useEffect(() => {
    let alive = true
    void loadCommands().then((cs) => {
      if (alive) setCommands(cs)
    })
    return () => {
      alive = false
    }
  }, [])

  const matches = useMemo(() => {
    const q = query.toLowerCase()
    return commands.filter(
      (c) => c.name.startsWith(q) || c.description.toLowerCase().includes(q)
    )
  }, [commands, query])

  useEffect(() => {
    onMatchesChange(matches)
  }, [matches, onMatchesChange])

  if (matches.length === 0) return null

  return (
    <div
      className="absolute right-3 bottom-full left-3 mb-2 overflow-hidden rounded-lg shadow-lg"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        zIndex: 30,
      }}
      role="listbox"
      aria-label="Slash commands"
    >
      {matches.map((c, i) => {
        const selected = i === selectedIndex
        return (
          <button
            key={c.name}
            type="button"
            role="option"
            aria-selected={selected}
            onMouseEnter={() => onHover(i)}
            onMouseDown={(e) => {
              e.preventDefault()
              onSelect(c)
            }}
            className="flex w-full items-baseline gap-2 px-3 py-2 text-left transition"
            style={{
              background: selected ? "var(--hover)" : "transparent",
              border: 0,
              cursor: "pointer",
            }}
          >
            <span
              className="font-mono text-[12px]"
              style={{ color: "var(--accent)" }}
            >
              /{c.name}
            </span>
            <span className="text-[11px]" style={{ color: "var(--ink-3)" }}>
              {c.arg_hint}
            </span>
            <span
              className="ml-auto truncate text-[11px]"
              style={{ color: "var(--ink-2)" }}
            >
              {c.description}
            </span>
          </button>
        )
      })}
    </div>
  )
}
