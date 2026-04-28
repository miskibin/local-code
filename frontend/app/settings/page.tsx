"use client"

import Link from "next/link"
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
} from "react"
import {
  ArrowLeft,
  Check,
  Database,
  FileText,
  Folder,
  Globe,
  Palette,
  ChevronRight,
  Loader2,
  Plus,
  Server,
  Sparkles,
  Terminal,
  Trash2,
  Wrench,
} from "lucide-react"
import { Markdown } from "@/app/_components/Markdown"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import type { MCPServer, Skill, Tool } from "@/lib/types"
import {
  ACCENTS,
  type AccentName,
  getStoredAccent,
  setStoredAccent,
} from "@/lib/accent"
import {
  FONT_PRESETS,
  type FontPreset,
  getStoredFontPreset,
  setStoredFontPreset,
} from "@/lib/font-preset"
import { AddServerDialog } from "../_components/AddServerDialog"

const SETTINGS_SECTION_IDS = [
  "appearance",
  "skills",
  "instructions",
  "mcp",
  "tools",
] as const

type SettingsSectionId = (typeof SETTINGS_SECTION_IDS)[number]

const SETTINGS_NAV: {
  id: SettingsSectionId
  label: string
  icon: ComponentType<{ className?: string }>
}[] = [
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "skills", label: "Skills", icon: Sparkles },
  { id: "instructions", label: "Instructions", icon: FileText },
  { id: "mcp", label: "MCP servers", icon: Server },
  { id: "tools", label: "Tools", icon: Wrench },
]

const settingsNavLinkClass =
  "lc-settings-nav-link flex w-full min-w-0 flex-row flex-nowrap items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13.5px] font-medium whitespace-nowrap text-[var(--ink-2)] no-underline outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"

/** Content Y from top of scrollport at which we switch the active nav item (stable TOC behavior). */
const SETTINGS_SCROLL_ACTIVATION_PX = 32
/** When this close to scroll bottom, highlight the last section (short final blocks). */
const SETTINGS_SCROLL_BOTTOM_SLACK_PX = 48

export default function SettingsPage() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const scrollRafRef = useRef(0)
  const [activeSection, setActiveSection] =
    useState<SettingsSectionId>("appearance")

  const updateActiveFromScroll = useCallback(() => {
    const root = scrollRef.current
    if (!root) return

    const scrollTop = root.scrollTop
    const lastId = SETTINGS_SECTION_IDS[SETTINGS_SECTION_IDS.length - 1]

    if (
      root.scrollHeight - root.clientHeight - scrollTop <=
      SETTINGS_SCROLL_BOTTOM_SLACK_PX
    ) {
      setActiveSection((p) => (p === lastId ? p : lastId))
      return
    }

    const activation = scrollTop + SETTINGS_SCROLL_ACTIVATION_PX
    const rootRect = root.getBoundingClientRect()
    let next: SettingsSectionId = SETTINGS_SECTION_IDS[0]

    for (const id of SETTINGS_SECTION_IDS) {
      const el = document.getElementById(id)
      if (!el) continue
      const elRect = el.getBoundingClientRect()
      const topInContent = elRect.top - rootRect.top + scrollTop
      if (topInContent <= activation) next = id
    }

    setActiveSection((prev) => (prev === next ? prev : next))
  }, [])

  useEffect(() => {
    const root = scrollRef.current
    if (!root) return

    const schedule = () => {
      if (scrollRafRef.current) return
      scrollRafRef.current = requestAnimationFrame(() => {
        scrollRafRef.current = 0
        updateActiveFromScroll()
      })
    }

    updateActiveFromScroll()
    root.addEventListener("scroll", schedule, { passive: true })
    const ro = new ResizeObserver(() => updateActiveFromScroll())
    ro.observe(root)

    return () => {
      root.removeEventListener("scroll", schedule)
      ro.disconnect()
      if (scrollRafRef.current) cancelAnimationFrame(scrollRafRef.current)
    }
  }, [updateActiveFromScroll])

  const scrollToSection = (id: SettingsSectionId) => {
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    })
    setActiveSection(id)
  }

  return (
    <div className="flex h-dvh flex-col" style={{ background: "var(--bg)" }}>
      <div
        className="flex items-center gap-3 px-6 py-3.5"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <Link
          href="/"
          aria-label="Back"
          className="inline-flex items-center justify-center rounded-md p-1.5 text-[var(--ink-2)] transition-colors hover:bg-[var(--accent-soft)] hover:text-[var(--accent-ink)]"
        >
          <ArrowLeft className="h-[17px] w-[17px]" />
        </Link>
        <div
          className="text-[15px] font-semibold"
          style={{ color: "var(--ink)" }}
        >
          Settings
        </div>
      </div>

      <div className="lc-settings-layout flex min-h-0 flex-1">
        <div
          className="flex w-[200px] flex-shrink-0 flex-col gap-1 px-3 py-4"
          style={{
            background: "var(--bg-soft)",
            borderRight:
              "1px solid color-mix(in oklab, var(--accent) 24%, var(--border))",
          }}
        >
          <nav
            aria-label="Settings sections"
            className="flex flex-col gap-0.5"
          >
            {SETTINGS_NAV.map(({ id, label, icon: Icon }) => (
              <a
                key={id}
                href={`#${id}`}
                className={settingsNavLinkClass}
                data-active={activeSection === id ? "true" : undefined}
                aria-current={activeSection === id ? "location" : undefined}
                onClick={(e) => {
                  e.preventDefault()
                  scrollToSection(id)
                }}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span className="min-w-0">{label}</span>
              </a>
            ))}
          </nav>
        </div>
        <div
          ref={scrollRef}
          className="lc-scroll lc-settings-main flex-1 overflow-y-auto px-10 py-8"
        >
          <div className="mx-auto max-w-[760px] space-y-16">
            <section id="appearance" className="scroll-mt-4">
              <AppearanceTab />
            </section>
            <section id="skills" className="scroll-mt-4">
              <SkillsTab />
            </section>
            <section id="instructions" className="scroll-mt-4">
              <InstructionsTab />
            </section>
            <section id="mcp" className="scroll-mt-4">
              <McpTab />
            </section>
            <section id="tools" className="scroll-mt-4 pb-4">
              <ToolsTab />
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionHeader({
  title,
  desc,
  right,
}: {
  title: string
  desc?: string
  right?: React.ReactNode
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2
          className="border-l-2 border-l-[var(--accent)] pl-3 text-[20px] font-semibold"
          style={{ letterSpacing: "-.01em" }}
        >
          {title}
        </h2>
        {desc && (
          <p className="mt-1 text-[13px]" style={{ color: "var(--ink-2)" }}>
            {desc}
          </p>
        )}
      </div>
      {right}
    </div>
  )
}

function McpTab() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [open, setOpen] = useState(false)

  const reload = useCallback(async () => {
    try {
      setServers(await api.listMCP())
    } catch (e) {
      console.error("listMCP", e)
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  const onToggle = async (s: MCPServer, enabled: boolean) => {
    await api.upsertMCP({ ...s, enabled })
    await reload()
  }

  const onDelete = async (name: string) => {
    await api.deleteMCP(name)
    await reload()
  }

  const onAdd = async (s: MCPServer) => {
    await api.upsertMCP(s)
    await reload()
  }

  return (
    <>
      <SectionHeader
        title="MCP servers"
        desc="Model Context Protocol servers expose tools the agent can call. Servers run locally."
        right={
          <Button onClick={() => setOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" /> Add server
          </Button>
        }
      />
      <div
        className="overflow-hidden rounded-xl"
        style={{
          border: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        {servers.length === 0 && (
          <div
            className="px-4 py-6 text-center text-[13px]"
            style={{ color: "var(--ink-3)" }}
          >
            No MCP servers configured. Click <strong>Add server</strong> to add
            one.
          </div>
        )}
        {servers.map((s, i) => (
          <McpRow
            key={s.name}
            server={s}
            index={i}
            onToggle={(v) => onToggle(s, v)}
            onDelete={() => onDelete(s.name)}
          />
        ))}
      </div>
      <p className="mt-3.5 text-xs" style={{ color: "var(--ink-3)" }}>
        Servers are launched as subprocesses on app start. Configuration lives
        in the backend SQLite database.
      </p>
      <AddServerDialog open={open} onOpenChange={setOpen} onAdd={onAdd} />
    </>
  )
}

function McpRow({
  server,
  index,
  onToggle,
  onDelete,
}: {
  server: MCPServer
  index: number
  onToggle: (v: boolean) => void
  onDelete: () => void
}) {
  const conn = server.connection ?? {}
  const cmd = [
    conn.command ?? "",
    ...((conn.args as string[] | undefined) ?? []),
  ]
    .join(" ")
    .trim()
  const Icon = guessIcon(server.name)
  return (
    <div
      className="flex items-start gap-3.5 px-4 py-3.5"
      style={{ borderTop: index === 0 ? 0 : "1px solid var(--border)" }}
    >
      <div
        className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg"
        style={{
          background: "var(--bg-soft)",
          border: "1px solid var(--border)",
          color: "var(--ink-2)",
        }}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 13.5,
              color: "var(--ink)",
            }}
          >
            {server.name}
          </span>
          <StatusBadge enabled={server.enabled} />
        </div>
        {cmd && (
          <div
            className="mt-1 truncate"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11.5,
              color: "var(--ink-3)",
            }}
          >
            {cmd}
          </div>
        )}
        <McpResolvedTools server={server} />
      </div>
      <Switch
        checked={server.enabled}
        onCheckedChange={onToggle}
        aria-label={`Toggle ${server.name}`}
      />
      <button
        onClick={onDelete}
        title="Delete"
        className="rounded-md p-1.5 transition"
        style={{ background: "transparent", color: "var(--ink-3)", border: 0 }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--hover)"
          e.currentTarget.style.color = "var(--red)"
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent"
          e.currentTarget.style.color = "var(--ink-3)"
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function McpResolvedTools({ server }: { server: MCPServer }) {
  if (!server.enabled) return null
  const tools = server.resolved_tools
  if (tools === undefined) return null
  if (tools.length === 0) {
    return (
      <div className="mt-1.5 text-[11px]" style={{ color: "var(--ink-3)" }}>
        No tools loaded
      </div>
    )
  }
  return (
    <div className="mt-1.5">
      <div
        className="text-[11px] font-medium"
        style={{ color: "var(--ink-2)" }}
      >
        {tools.length} tool{tools.length === 1 ? "" : "s"}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {tools.map((t) => (
          <span
            key={t}
            className="rounded-md px-1.5 py-0.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10.5,
              color: "var(--ink)",
              background: "var(--bg-soft)",
              border: "1px solid var(--border)",
            }}
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11.5px] font-medium"
      style={{
        background: enabled ? "var(--green-soft)" : "#f4f4f4",
        color: enabled ? "var(--green)" : "var(--ink-3)",
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: enabled ? "var(--green)" : "var(--ink-4)" }}
      />
      {enabled ? "Enabled" : "Disabled"}
    </span>
  )
}

function guessIcon(name: string) {
  const n = name.toLowerCase()
  if (n.includes("file") || n.includes("fs")) return Folder
  if (n.includes("web") || n.includes("http") || n.includes("fetch"))
    return Globe
  if (n.includes("sql") || n.includes("db")) return Database
  if (n.includes("shell") || n.includes("term")) return Terminal
  return Server
}

const TOOL_SECTION_HEADER =
  "px-4 py-2 uppercase border-b border-[var(--border)]" as const

const MAX_TOOL_SECTIONS = 3

type ToolSection = { id: string; title: string; tools: Tool[] }

type BuiltinFoldDef = {
  id: string
  title: string
  sourceIds: readonly string[]
}

const BUILTIN_FOLD_TO_THREE: BuiltinFoldDef[] = [
  {
    id: "builtin-fold-0",
    title: "Data & execution",
    sourceIds: ["builtin-data", "builtin-code"],
  },
  {
    id: "builtin-fold-1",
    title: "Web & documents",
    sourceIds: ["builtin-web", "builtin-outputs"],
  },
  {
    id: "builtin-fold-2",
    title: "Agent, UI & other",
    sourceIds: ["builtin-agent", "builtin-other"],
  },
]

function foldBuiltinSectionsToThree(biSecs: ToolSection[]): ToolSection[] {
  const byId = Object.fromEntries(biSecs.map((s) => [s.id, s.tools]))
  const out: ToolSection[] = []
  for (const def of BUILTIN_FOLD_TO_THREE) {
    const tools = def.sourceIds
      .flatMap((id) => byId[id] ?? [])
      .sort((a, b) => a.name.localeCompare(b.name))
    if (tools.length > 0) {
      out.push({ id: def.id, title: def.title, tools })
    }
  }
  return out
}

type BuiltinTypeDef = { id: string; title: string; names: readonly string[] }

const BUILTIN_TYPE_ORDER: BuiltinTypeDef[] = [
  {
    id: "builtin-data",
    title: "Data & SQL",
    names: ["sql_query", "read_table_summary"],
  },
  { id: "builtin-code", title: "Code & execution", names: ["python_exec"] },
  { id: "builtin-web", title: "Web & fetch", names: ["web_fetch"] },
  {
    id: "builtin-outputs",
    title: "Documents & email",
    names: ["email_draft", "generate_pptx"],
  },
  { id: "builtin-agent", title: "Agent & UI", names: ["quiz"] },
]

function builtinTypeIdForName(name: string): string | null {
  for (const def of BUILTIN_TYPE_ORDER) {
    if (def.names.includes(name)) return def.id
  }
  return null
}

function buildBuiltinSections(tools: Tool[]): ToolSection[] {
  if (tools.length === 0) return []
  const byId: Record<string, Tool[]> = {}
  const unknown: Tool[] = []
  for (const t of tools) {
    const id = builtinTypeIdForName(t.name)
    if (id) {
      ;(byId[id] ||= []).push(t)
    } else {
      unknown.push(t)
    }
  }
  const sections: ToolSection[] = []
  for (const def of BUILTIN_TYPE_ORDER) {
    const list = byId[def.id]
    if (list?.length) {
      sections.push({
        id: def.id,
        title: def.title,
        tools: [...list].sort((a, b) => a.name.localeCompare(b.name)),
      })
    }
  }
  if (unknown.length > 0) {
    sections.push({
      id: "builtin-other",
      title: "Other built-in",
      tools: [...unknown].sort((a, b) => a.name.localeCompare(b.name)),
    })
  }
  return sections
}

function capToolSectionsAtMax(sections: ToolSection[]): ToolSection[] {
  if (sections.length <= MAX_TOOL_SECTIONS) return sections

  const biSecs = sections.filter((s) => s.id.startsWith("builtin-"))
  const mcpSecs = sections.filter((s) => s.id.startsWith("mcp:"))

  if (mcpSecs.length === 0 && biSecs.length > MAX_TOOL_SECTIONS) {
    return foldBuiltinSectionsToThree(biSecs)
  }

  const biTools = biSecs
    .flatMap((s) => s.tools)
    .sort((a, b) => a.name.localeCompare(b.name))

  const out: ToolSection[] = []
  if (biTools.length > 0) {
    out.push({ id: "builtin", title: "Built-in", tools: biTools })
  }

  const budget = MAX_TOOL_SECTIONS - out.length
  if (budget <= 0) {
    return out.slice(0, MAX_TOOL_SECTIONS)
  }

  if (mcpSecs.length <= budget) {
    out.push(...[...mcpSecs].sort((a, b) => a.title.localeCompare(b.title)))
    return out
  }

  const byCount = [...mcpSecs].sort(
    (a, b) => b.tools.length - a.tools.length || a.title.localeCompare(b.title)
  )
  const keepCount = Math.max(0, budget - 1)
  const kept = byCount.slice(0, keepCount)
  const mergedTools = byCount.slice(keepCount).flatMap((s) => s.tools)
  const sortTools = (ts: Tool[]) =>
    [...ts].sort((a, b) => a.name.localeCompare(b.name))
  for (const s of kept) {
    out.push({ id: s.id, title: s.title, tools: sortTools(s.tools) })
  }
  if (mergedTools.length > 0) {
    out.push({
      id: "mcp:other",
      title: "Other MCP",
      tools: sortTools(mergedTools),
    })
  }
  return out
}

function buildToolSections(tools: Tool[]): ToolSection[] {
  const builtin = tools.filter((t) => t.source !== "mcp")
  const mcp = tools.filter((t) => t.source === "mcp")
  const sections: ToolSection[] = [...buildBuiltinSections(builtin)]

  const byServer: Record<string, Tool[]> = {}
  for (const t of mcp) {
    const key = t.server?.trim() || "MCP"
    ;(byServer[key] ||= []).push(t)
  }
  const mcpEntries = Object.entries(byServer).map(([title, list]) => ({
    title,
    tools: list,
  }))
  mcpEntries.sort((a, b) => a.title.localeCompare(b.title))
  for (const e of mcpEntries) {
    sections.push({
      id: `mcp:${e.title}`,
      title: e.title,
      tools: e.tools,
    })
  }
  return capToolSectionsAtMax(sections)
}

function ToolDescription({ text }: { text: string }) {
  const oneLine = text.trim().split(/\s+/).join(" ")
  return (
    <div
      className="mt-0.5 line-clamp-2 text-[12.5px] leading-snug"
      style={{ color: "var(--ink-2)" }}
      title={oneLine}
    >
      {oneLine}
    </div>
  )
}

function ToolsTab() {
  const [tools, setTools] = useState<Tool[]>([])

  const reload = useCallback(async () => {
    try {
      setTools(await api.listTools())
    } catch (e) {
      console.error("listTools", e)
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  const enabledCount = useMemo(
    () => tools.filter((t) => t.enabled).length,
    [tools]
  )

  const sections = useMemo(() => buildToolSections(tools), [tools])

  const onToggle = async (name: string, enabled: boolean) => {
    setTools((p) => p.map((t) => (t.name === name ? { ...t, enabled } : t)))
    try {
      await api.setTool(name, enabled)
    } catch (e) {
      console.error("setTool", e)
      reload()
    }
  }

  return (
    <>
      <SectionHeader
        title="Tools"
        desc={`${enabledCount} of ${tools.length} tools available to the agent. Disabled tools are hidden from the model entirely.`}
      />
      {tools.length === 0 ? (
        <div
          className="overflow-hidden rounded-xl px-4 py-6 text-center text-[13px]"
          style={{
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--ink-3)",
          }}
        >
          No tools discovered.
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          {sections.map((sec) => (
            <div
              key={sec.id}
              className="overflow-hidden rounded-xl"
              style={{
                border: "1px solid var(--border)",
                background: "var(--surface)",
              }}
            >
              <div
                className={TOOL_SECTION_HEADER}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: ".04em",
                  color: "var(--ink-3)",
                  background: "var(--bg-soft)",
                }}
              >
                {sec.title}
              </div>
              <div
                className="grid grid-cols-1 gap-px md:grid-cols-2"
                style={{ background: "var(--border)" }}
              >
                {sec.tools.map((t) => (
                  <div
                    key={t.name}
                    className="flex items-start gap-3.5 bg-[var(--surface)] px-4 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 13,
                          color: "var(--ink)",
                        }}
                      >
                        {t.name}
                      </div>
                      {t.description ? (
                        <ToolDescription text={t.description} />
                      ) : null}
                    </div>
                    <Switch
                      className="mt-0.5 shrink-0"
                      checked={t.enabled}
                      onCheckedChange={(v) => onToggle(t.name, v)}
                      aria-label={`Toggle ${t.name}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function AppearanceTab() {
  const [accent, setAccent] = useState<AccentName>("blue")
  const [fontPreset, setFontPreset] = useState<FontPreset>("mono")

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- sync from localStorage after mount (boot scripts already set CSS) */
    setAccent(getStoredAccent())
    setFontPreset(getStoredFontPreset())
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [])

  const onPickAccent = (name: AccentName) => {
    setAccent(name)
    setStoredAccent(name)
  }

  const onPickFont = (name: FontPreset) => {
    setFontPreset(name)
    setStoredFontPreset(name)
  }

  const settingsGroupHeader =
    "px-4 py-2 uppercase border-b border-[var(--border)]" as const

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Appearance"
        desc="Accent for focus and primary actions. Body type follows your font preset everywhere in the app, including this page."
      />

      <div
        className="overflow-hidden rounded-xl"
        style={{
          border: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        <div
          className={settingsGroupHeader}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: "0.04em",
            color: "var(--ink-3)",
            background: "var(--bg-soft)",
          }}
        >
          Accent
        </div>
        <div className="p-4 sm:p-5">
          <p
            className="mb-3 text-[12px] leading-snug"
            style={{ color: "var(--ink-2)" }}
          >
            Links, buttons, and focus rings use the selected hue.
          </p>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            {(Object.keys(ACCENTS) as AccentName[]).map((name) => {
              const { label, color } = ACCENTS[name]
              const active = accent === name
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => onPickAccent(name)}
                  aria-pressed={active}
                  aria-label={`Accent: ${label}`}
                  className="group relative flex flex-col gap-2.5 rounded-lg border p-3 text-left transition-[border-color,background-color,box-shadow] duration-150 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)]"
                  style={{
                    cursor: "pointer",
                    borderColor: active ? color : "var(--border)",
                    background: active
                      ? `color-mix(in oklab, ${color} 14%, var(--surface))`
                      : "var(--bg-soft)",
                    boxShadow: active
                      ? `0 0 0 1px ${color}, 0 4px 14px -4px color-mix(in oklab, ${color} 40%, transparent)`
                      : undefined,
                  }}
                >
                  <div
                    className="h-1.5 w-full rounded-sm"
                    style={{ background: color }}
                  />
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className="text-[12px] font-semibold"
                      style={{ color: "var(--ink)" }}
                    >
                      {label}
                    </span>
                    {active && (
                      <Check
                        className="mt-0.5 h-3.5 w-3.5 shrink-0"
                        style={{ color }}
                        strokeWidth={2.5}
                        aria-hidden
                      />
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div
          className={settingsGroupHeader}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: "0.04em",
            color: "var(--ink-3)",
            background: "var(--bg-soft)",
            borderTop: "1px solid var(--border)",
          }}
        >
          Body font
        </div>
        <div className="p-4 sm:p-5">
          <p
            className="mb-3 text-[12px] leading-snug"
            style={{ color: "var(--ink-2)" }}
          >
            Sample line uses each preset so you can compare. Sans uses Inter.
          </p>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {(Object.keys(FONT_PRESETS) as FontPreset[]).map((name) => {
              const { label, stack } = FONT_PRESETS[name]
              const active = fontPreset === name
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => onPickFont(name)}
                  aria-pressed={active}
                  aria-label={`Font: ${label}`}
                  className="rounded-lg border p-3 text-left transition-[border-color,background-color,box-shadow] duration-150 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)]"
                  style={{
                    cursor: "pointer",
                    borderColor: active ? "var(--accent)" : "var(--border)",
                    background: active
                      ? "var(--accent-soft)"
                      : "var(--bg-soft)",
                    boxShadow: active
                      ? "0 1px 0 color-mix(in oklab, var(--accent) 22%, transparent)"
                      : undefined,
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span
                          className="text-[11px] font-medium tracking-[0.06em] uppercase"
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--ink-3)",
                          }}
                        >
                          {name}
                        </span>
                        <span
                          className="text-[12px] font-semibold"
                          style={{
                            color: active ? "var(--accent-ink)" : "var(--ink)",
                          }}
                        >
                          {label}
                        </span>
                      </div>
                      <p
                        className="mt-2 line-clamp-2 text-[11.5px] leading-relaxed"
                        style={{
                          fontFamily: stack,
                          color: "var(--ink-2)",
                        }}
                      >
                        The quick brown fox jumps over the lazy dog.
                      </p>
                    </div>
                    {active && (
                      <Check
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--accent)]"
                        strokeWidth={2.5}
                        aria-hidden
                      />
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <p className="text-xs" style={{ color: "var(--ink-3)" }}>
        Stored in this browser only.
      </p>
    </div>
  )
}

const SKILL_FRONTMATTER_RE = /^---\s*\n[\s\S]*?\n---\s*\n+/

function SkillsTab() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [viewer, setViewer] = useState<{
    name: string | null
    markdown: string | null
    loading: boolean
    error: string | null
  }>({ name: null, markdown: null, loading: false, error: null })

  const reload = useCallback(async () => {
    try {
      setSkills(await api.listSkills())
    } catch (e) {
      console.error("listSkills", e)
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  const enabledCount = useMemo(
    () => skills.filter((s) => s.enabled).length,
    [skills]
  )

  const onToggle = async (name: string, enabled: boolean) => {
    setSkills((p) => p.map((s) => (s.name === name ? { ...s, enabled } : s)))
    try {
      await api.setSkill(name, enabled)
    } catch (e) {
      console.error("setSkill", e)
      reload()
    }
  }

  const openSkillViewer = (name: string) => {
    setViewer({ name, markdown: null, loading: true, error: null })
    void (async () => {
      try {
        const r = await api.getSkillContent(name)
        setViewer((v) =>
          v.name === name
            ? { ...v, markdown: r.markdown, loading: false, error: null }
            : v
        )
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        setViewer((v) =>
          v.name === name ? { ...v, loading: false, error: msg } : v
        )
      }
    })()
  }

  const viewerOpen = viewer.name !== null
  const viewerSkill = viewer.name
    ? skills.find((x) => x.name === viewer.name)
    : undefined

  return (
    <>
      <SectionHeader
        title="Skills"
        desc={`${enabledCount} of ${skills.length} skills enabled. Skills are markdown playbooks the agent reads when relevant. Click a row to read the full playbook.`}
      />
      <div
        className="overflow-hidden rounded-xl"
        style={{
          border: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        {skills.map((s, i) => (
          <div
            key={s.name}
            className="flex items-start gap-2 px-4 py-3 transition-colors focus-within:bg-[var(--accent-soft)] hover:bg-[var(--accent-soft)]"
            style={{ borderTop: i === 0 ? 0 : "1px solid var(--border)" }}
          >
            <button
              type="button"
              className="flex min-w-0 flex-1 items-start gap-3.5 rounded-md py-0.5 pr-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label={`View full playbook: ${s.name}`}
              onClick={() => openSkillViewer(s.name)}
            >
              <Sparkles
                className="mt-0.5 h-4 w-4 flex-shrink-0"
                style={{ color: "var(--ink-3)" }}
              />
              <div className="min-w-0 flex-1">
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 13,
                    color: "var(--ink)",
                  }}
                >
                  {s.name}
                </div>
                {s.description && (
                  <div
                    className="mt-0.5 text-[12.5px]"
                    style={{ color: "var(--ink-2)" }}
                  >
                    {s.description}
                  </div>
                )}
              </div>
              <ChevronRight
                className="mt-0.5 h-4 w-4 flex-shrink-0"
                style={{ color: "var(--ink-3)" }}
                aria-hidden
              />
            </button>
            <Switch
              className="mt-0.5 shrink-0"
              checked={s.enabled}
              onCheckedChange={(v) => onToggle(s.name, v)}
              aria-label={`Toggle ${s.name}`}
            />
          </div>
        ))}
        {skills.length === 0 && (
          <div
            className="px-4 py-6 text-center text-[13px]"
            style={{ color: "var(--ink-3)" }}
          >
            No skills installed.
          </div>
        )}
      </div>

      <Dialog
        open={viewerOpen}
        onOpenChange={(o) => {
          if (!o) {
            setViewer({
              name: null,
              markdown: null,
              loading: false,
              error: null,
            })
          }
        }}
      >
        <DialogContent
          showCloseButton
          className="flex max-h-[min(90vh,920px)] w-[calc(100%-1.5rem)] max-w-[min(96vw,1200px)] flex-col gap-0 overflow-hidden p-0 sm:max-w-[min(96vw,1200px)]"
        >
          <DialogHeader className="shrink-0 border-b px-5 py-4 pr-12">
            <DialogTitle
              className="font-mono text-base tracking-tight"
              style={{ color: "var(--ink)" }}
            >
              {viewer.name ?? "Skill"}
            </DialogTitle>
            {viewerSkill?.description && (
              <p
                className="text-[13px] leading-snug font-normal"
                style={{ color: "var(--ink-2)" }}
              >
                {viewerSkill.description}
              </p>
            )}
          </DialogHeader>
          <div
            className="lc-scroll min-h-0 flex-1 overflow-y-auto px-5 py-4"
            style={{ background: "var(--bg-soft)" }}
          >
            {viewer.loading && (
              <div
                className="flex items-center gap-2 text-[13px]"
                style={{ color: "var(--ink-2)" }}
              >
                <Loader2
                  className="h-4 w-4 shrink-0 animate-spin"
                  aria-hidden
                />
                Loading playbook…
              </div>
            )}
            {viewer.error && (
              <p className="text-[13px] text-destructive">{viewer.error}</p>
            )}
            {!viewer.loading &&
              !viewer.error &&
              viewer.markdown !== null &&
              viewer.name !== null && (
                <Markdown
                  text={viewer.markdown.replace(SKILL_FRONTMATTER_RE, "")}
                />
              )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function InstructionsTab() {
  const [content, setContent] = useState("")
  const [saved, setSaved] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [mode, setMode] = useState<"edit" | "preview">("edit")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const r = await api.getInstructions()
        if (cancelled) return
        setContent(r.content)
        setSaved(r.content)
      } catch (e) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const dirty = content !== saved
  const charCount = content.length
  const tokenEstimate = Math.ceil(charCount / 4)

  const onSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const r = await api.setInstructions(content)
      setSaved(r.content)
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <SectionHeader
        title="Custom instructions"
        desc="Always-on system prompt addendum applied to every chat. Markdown supported."
        right={
          <div
            className="inline-flex overflow-hidden rounded-md"
            style={{ border: "1px solid var(--border)" }}
          >
            <button
              type="button"
              onClick={() => setMode("edit")}
              aria-pressed={mode === "edit"}
              className="px-3 py-1.5 text-[12px] font-medium transition-colors"
              style={{
                cursor: "pointer",
                background:
                  mode === "edit" ? "var(--accent-soft)" : "transparent",
                color: mode === "edit" ? "var(--accent-ink)" : "var(--ink-2)",
              }}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setMode("preview")}
              aria-pressed={mode === "preview"}
              className="px-3 py-1.5 text-[12px] font-medium transition-colors"
              style={{
                cursor: "pointer",
                background:
                  mode === "preview" ? "var(--accent-soft)" : "transparent",
                color:
                  mode === "preview" ? "var(--accent-ink)" : "var(--ink-2)",
                borderLeft: "1px solid var(--border)",
              }}
            >
              Preview
            </button>
          </div>
        }
      />

      <div
        className="overflow-hidden rounded-xl"
        style={{
          border: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        {loading ? (
          <div
            className="flex items-center gap-2 px-4 py-6 text-[13px]"
            style={{ color: "var(--ink-3)" }}
          >
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Loading…
          </div>
        ) : mode === "edit" ? (
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="e.g. Always answer concisely. Prefer code examples in Python. Never include disclaimers."
            rows={20}
            className="resize-y border-0 focus-visible:ring-0"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              minHeight: 380,
              background: "var(--surface)",
            }}
          />
        ) : content.trim().length === 0 ? (
          <div
            className="px-4 py-6 text-[13px]"
            style={{ color: "var(--ink-3)" }}
          >
            Nothing to preview yet.
          </div>
        ) : (
          <div className="px-4 py-3">
            <Markdown text={content} />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="text-[12px]" style={{ color: "var(--ink-3)" }}>
          {charCount.toLocaleString()} characters · ~
          {tokenEstimate.toLocaleString()} tokens
        </div>
        <div className="flex items-center gap-3">
          {error && (
            <span className="text-[12px] text-destructive">{error}</span>
          )}
          {dirty && !saving && (
            <span className="text-[12px]" style={{ color: "var(--ink-3)" }}>
              Unsaved changes
            </span>
          )}
          <Button
            onClick={onSave}
            disabled={!dirty || saving || loading}
            className="gap-1.5"
          >
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </Button>
        </div>
      </div>

      <p className="mt-3 text-xs" style={{ color: "var(--ink-3)" }}>
        Appended to the agent&rsquo;s system prompt on every chat turn. Token
        count is a rough estimate (~4 chars per token).
      </p>
    </>
  )
}
