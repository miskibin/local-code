"use client"

import { useMemo } from "react"
import type { Tool } from "@/lib/types"
import { cn } from "@/lib/utils"
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxGroup,
  ComboboxInput,
  ComboboxItem,
  ComboboxLabel,
  ComboboxList,
  ComboboxSeparator,
} from "@/components/ui/combobox"

type Props = {
  tools: Tool[]
  value: string
  onPick: (tool: Tool | null) => void
}

export function ToolPicker({ tools, value, onPick }: Props) {
  const { builtins, mcp } = useMemo(() => {
    const b: Tool[] = []
    const m: Tool[] = []
    for (const t of tools) {
      if (!t.enabled) continue
      if (t.source === "mcp") m.push(t)
      else b.push(t)
    }
    b.sort((a, b) => a.name.localeCompare(b.name))
    m.sort((a, b) => a.name.localeCompare(b.name))
    return { builtins: b, mcp: m }
  }, [tools])

  const handleChange = (next: string | null) => {
    if (!next) {
      onPick(null)
      return
    }
    const found = tools.find((t) => t.name === next) ?? null
    onPick(found)
  }

  return (
    <div className="w-full max-w-md">
      <Combobox
        items={[...builtins, ...mcp].map((t) => t.name)}
        value={value || null}
        onValueChange={handleChange}
      >
        <ComboboxInput
          placeholder="Pick a tool…"
          showClear
          className={cn(
            "w-full border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink)] shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"
          )}
        />
        <ComboboxContent>
          <ComboboxList>
          <ComboboxEmpty>No tools match.</ComboboxEmpty>
          {builtins.length > 0 && (
            <ComboboxGroup>
              <ComboboxLabel>Built-in</ComboboxLabel>
              {builtins.map((t) => (
                <ComboboxItem key={t.name} value={t.name}>
                  <ToolRow tool={t} />
                </ComboboxItem>
              ))}
            </ComboboxGroup>
          )}
          {builtins.length > 0 && mcp.length > 0 && <ComboboxSeparator />}
          {mcp.length > 0 && (
            <ComboboxGroup>
              <ComboboxLabel>MCP</ComboboxLabel>
              {mcp.map((t) => (
                <ComboboxItem key={t.name} value={t.name}>
                  <ToolRow tool={t} />
                </ComboboxItem>
              ))}
            </ComboboxGroup>
          )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </div>
  )
}

function ToolRow({ tool }: { tool: Tool }) {
  return (
    <div className="flex w-full min-w-0 flex-col gap-0.5">
      <div className="flex items-center gap-2">
        <span className="truncate font-medium">{tool.name}</span>
        {tool.source === "mcp" && (
          <span
            className="rounded px-1.5 py-[1px] text-[10px] font-medium tracking-wide uppercase"
            style={{
              background: "var(--hover)",
              color: "var(--ink-3)",
              border: "1px solid var(--border)",
            }}
            title={
              tool.server ? `MCP server: ${tool.server}` : "External MCP tool"
            }
          >
            external
          </span>
        )}
      </div>
      {tool.description && (
        <span
          className="line-clamp-1 text-xs"
          style={{ color: "var(--ink-3)" }}
        >
          {tool.description}
        </span>
      )}
    </div>
  )
}
