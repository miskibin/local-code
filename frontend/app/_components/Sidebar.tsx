"use client"

import {
  ChevronRight,
  Cpu,
  Database,
  PanelLeft,
  Pencil,
  Search,
  Settings,
  Trash2,
} from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import type { Artifact, Session } from "@/lib/types"

type Props = {
  collapsed: boolean
  onToggle: () => void
  sessions: Session[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onSearch: () => void
  onDeleteSession: (id: string) => void
  artifacts: Artifact[]
  onOpenArtifact: (a: Artifact) => void
  onDeleteArtifact: (id: string) => void
}

export function Sidebar({
  collapsed,
  onToggle,
  sessions,
  activeId,
  onSelect,
  onNew,
  onSearch,
  onDeleteSession,
  artifacts,
  onOpenArtifact,
  onDeleteArtifact,
}: Props) {
  const [chatsOpen, setChatsOpen] = useState(true)
  const [artifactsOpen, setArtifactsOpen] = useState(true)

  if (collapsed) {
    return (
      <div
        className="lc-sidebar-wrap flex flex-shrink-0 flex-col items-center gap-1.5 py-3"
        style={{
          width: 56,
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border)",
        }}
      >
        <SideIconBtn label="Open sidebar" onClick={onToggle}>
          <PanelLeft className="h-4 w-4" />
        </SideIconBtn>
        <SideIconBtn label="New chat" onClick={onNew}>
          <Pencil className="h-4 w-4" />
        </SideIconBtn>
        <SideIconBtn label="Search" onClick={onSearch}>
          <Search className="h-4 w-4" />
        </SideIconBtn>
        <div className="flex-1" />
        <Link href="/settings" aria-label="Settings">
          <SideIconBtn label="Settings">
            <Settings className="h-4 w-4" />
          </SideIconBtn>
        </Link>
      </div>
    )
  }

  return (
    <div
      className="lc-sidebar-wrap flex min-w-0 flex-shrink-0 flex-col"
      style={{
        width: 260,
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border)",
      }}
    >
      <div className="flex items-center justify-end px-2.5 pt-2.5 pb-1.5">
        <button
          onClick={onToggle}
          title="Collapse sidebar"
          className="inline-flex items-center justify-center rounded-md p-1.5"
          style={{
            background: "transparent",
            border: 0,
            color: "var(--ink-2)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--hover)"
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent"
          }}
        >
          <PanelLeft className="h-[17px] w-[17px]" />
        </button>
      </div>

      <div className="px-2 pb-0.5">
        <SideRow icon={<Pencil className="h-4 w-4" />} onClick={onNew}>
          New chat
        </SideRow>
        <SideRow icon={<Search className="h-4 w-4" />} onClick={onSearch}>
          Search chats
        </SideRow>
      </div>

      <div className="lc-scroll flex-1 overflow-y-auto px-2 pt-3 pb-2">
        <SectionHead
          open={chatsOpen}
          onToggle={() => setChatsOpen((o) => !o)}
          count={sessions.length + 1}
        >
          Chats
        </SectionHead>
        {chatsOpen && (
          <>
            <button
              onClick={() => onSelect("demo-subagent")}
              title="SQL Analyst demo"
              className="mb-px block w-full truncate rounded-md py-1.5 pr-2.5 pl-2.5 text-left"
              style={{
                background:
                  activeId === "demo-subagent" ? "var(--hover)" : "transparent",
                color: "var(--ink)",
                border: 0,
                fontSize: 13.5,
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                if (activeId !== "demo-subagent")
                  e.currentTarget.style.background = "var(--hover)"
              }}
              onMouseLeave={(e) => {
                if (activeId !== "demo-subagent")
                  e.currentTarget.style.background = "transparent"
              }}
            >
              <span className="inline-flex items-center gap-2">
                <span
                  className="text-[10px] uppercase"
                  style={{
                    color: "var(--accent-ink)",
                    background: "var(--accent-soft)",
                    padding: "1px 5px",
                    borderRadius: 4,
                    fontWeight: 500,
                    letterSpacing: ".04em",
                  }}
                >
                  Demo
                </span>
                <span>SQL Analyst — Q1 breakdown</span>
              </span>
            </button>
            {sessions.map((s) => (
              <ChatRow
                key={s.id}
                session={s}
                active={s.id === activeId}
                onSelect={() => onSelect(s.id)}
                onDelete={() => onDeleteSession(s.id)}
              />
            ))}
          </>
        )}

        <div className="h-3.5" />

        <SectionHead
          open={artifactsOpen}
          onToggle={() => setArtifactsOpen((o) => !o)}
          count={artifacts.length}
        >
          Artifacts
        </SectionHead>
        {artifactsOpen &&
          (artifacts.length === 0 ? (
            <div
              className="px-2.5 py-2"
              style={{ fontSize: 12, color: "var(--ink-3)" }}
            >
              Saved tables and charts appear here.
            </div>
          ) : (
            artifacts.map((a) => (
              <ArtifactRow
                key={a.id}
                artifact={a}
                onOpen={() => onOpenArtifact(a)}
                onDelete={() => onDeleteArtifact(a.id)}
              />
            ))
          ))}
      </div>

      <div className="p-2" style={{ borderTop: "1px solid var(--border)" }}>
        <Link href="/settings" className="block">
          <SideRow icon={<Settings className="h-4 w-4" />}>Settings</SideRow>
        </Link>
      </div>
    </div>
  )
}

function ArtifactRow({
  artifact,
  onOpen,
  onDelete,
}: {
  artifact: Artifact
  onOpen: () => void
  onDelete: () => void
}) {
  return (
    <div className="group/row relative">
      <button
        onClick={onOpen}
        title={artifact.title}
        className="mb-px flex w-full items-center gap-2 truncate rounded-md py-1.5 pr-9 pl-2.5 text-left"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink)",
          fontSize: 13,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--hover)"
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent"
        }}
      >
        <span
          className="inline-flex flex-shrink-0"
          style={{ color: "var(--accent)" }}
        >
          {artifact.kind === "table" ? (
            <Database className="h-3 w-3" />
          ) : (
            <Cpu className="h-3 w-3" />
          )}
        </span>
        <span className="flex-1 truncate">{artifact.title}</span>
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        title="Delete"
        className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md p-1 opacity-0 transition group-hover/row:opacity-100"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-3)",
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function ChatRow({
  session,
  active,
  onSelect,
  onDelete,
}: {
  session: Session
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div className="group/row relative">
      <button
        onClick={onSelect}
        title={session.title || "Untitled"}
        className="mb-px block w-full truncate rounded-md py-1.5 pr-9 pl-2.5 text-left"
        style={{
          background: active ? "var(--hover)" : "transparent",
          color: "var(--ink)",
          border: 0,
          fontSize: 13.5,
          cursor: "pointer",
        }}
        onMouseEnter={(e) => {
          if (!active) e.currentTarget.style.background = "var(--hover)"
        }}
        onMouseLeave={(e) => {
          if (!active) e.currentTarget.style.background = "transparent"
        }}
      >
        {session.title || "Untitled"}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        title="Delete"
        className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md p-1 opacity-0 transition group-hover/row:opacity-100"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-3)",
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function SectionHead({
  open,
  onToggle,
  count,
  children,
}: {
  open: boolean
  onToggle: () => void
  count: number
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center gap-1.5 px-2.5 pt-1 pb-1 uppercase"
      style={{
        background: "transparent",
        border: 0,
        color: "var(--ink-3)",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: ".04em",
      }}
    >
      <span
        className="inline-flex transition-transform"
        style={{ transform: open ? "rotate(90deg)" : "none" }}
      >
        <ChevronRight className="h-3 w-3" />
      </span>
      <span>{children}</span>
      <span
        className="ml-auto"
        style={{ color: "var(--ink-4)", fontWeight: 400 }}
      >
        {count}
      </span>
    </button>
  )
}

function SideRow({
  icon,
  children,
  onClick,
}: {
  icon: React.ReactNode
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13.5px]"
      style={{
        background: "transparent",
        border: 0,
        color: "var(--ink)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      <span className="inline-flex" style={{ color: "var(--ink-2)" }}>
        {icon}
      </span>
      <span>{children}</span>
    </button>
  )
}

function SideIconBtn({
  label,
  onClick,
  children,
}: {
  label: string
  onClick?: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      className="rounded-md p-2"
      style={{ background: "transparent", border: 0, color: "var(--ink-2)" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      {children}
    </button>
  )
}
