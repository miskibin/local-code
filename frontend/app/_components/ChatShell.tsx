"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { nanoid } from "nanoid"
import { api } from "@/lib/api"
import type { Artifact, Session } from "@/lib/types"
import { ArtifactModal } from "./ArtifactModal"
import { ChatView } from "./ChatView"
import { SearchDialog } from "./SearchDialog"
import { Sidebar } from "./Sidebar"
import { DEMO_SUBAGENT_STEPS } from "./sampleData"

export function ChatShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(() => nanoid())
  const [sessions, setSessions] = useState<Session[]>([])
  const [savedArtifacts, setSavedArtifacts] = useState<Artifact[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null)

  const refreshArtifacts = useCallback(async () => {
    try {
      setSavedArtifacts(await api.listArtifacts())
    } catch (e) {
      console.error("listArtifacts", e)
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
    } catch (e) {
      console.error("listSessions", e)
    }
  }, [])

  useEffect(() => {
    refreshSessions()
    refreshArtifacts()
  }, [refreshSessions, refreshArtifacts])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setSearchOpen((o) => !o)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const onNew = () => {
    setActiveSessionId(nanoid())
  }

  const onSelectSession = (id: string) => {
    setActiveSessionId(id)
  }

  const onDeleteSession = async (id: string) => {
    try {
      await api.deleteSession(id)
      if (id === activeSessionId) setActiveSessionId(nanoid())
      await refreshSessions()
    } catch (e) {
      console.error("deleteSession", e)
    }
  }

  const onDeleteArtifact = async (id: string) => {
    try {
      await api.deleteArtifact(id)
      if (openArtifact?.id === id) setOpenArtifact(null)
      await refreshArtifacts()
    } catch (e) {
      console.error("deleteArtifact", e)
    }
  }

  const onFirstUserMessage = useCallback(
    async (text: string) => {
      const exists = sessions.some((s) => s.id === activeSessionId)
      if (exists) return
      try {
        await api.createSession({
          id: activeSessionId,
          title: text.slice(0, 40) || "Untitled",
        })
        await refreshSessions()
      } catch (e) {
        console.error("createSession", e)
      }
    },
    [activeSessionId, sessions, refreshSessions]
  )

  const savedMap = useMemo(() => {
    const m: Record<string, boolean> = {}
    for (const a of savedArtifacts) m[a.id] = true
    return m
  }, [savedArtifacts])

  const onSaveArtifact = async (a: Artifact) => {
    try {
      await api.saveArtifact({ ...a, session_id: activeSessionId })
      await refreshArtifacts()
    } catch (e) {
      console.error("saveArtifact", e)
    }
  }

  const isDemo = activeSessionId === "demo-subagent"
  const seedSteps = isDemo ? DEMO_SUBAGENT_STEPS : undefined
  const demoUserText = isDemo
    ? "Get me a Q1 sales breakdown by region — delegate to the SQL analyst."
    : undefined
  const demoAssistantText = isDemo
    ? "Done — full breakdown above. Want me to send the Data Scientist next to chart this?"
    : undefined

  return (
    <main
      className="flex h-dvh w-full overflow-hidden"
      style={{ background: "var(--bg)" }}
    >
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={onSelectSession}
        onNew={onNew}
        onSearch={() => setSearchOpen(true)}
        onDeleteSession={onDeleteSession}
        artifacts={savedArtifacts}
        onOpenArtifact={setOpenArtifact}
        onDeleteArtifact={onDeleteArtifact}
      />
      <ChatView
        sessionId={activeSessionId}
        onFirstUserMessage={onFirstUserMessage}
        savedArtifacts={savedMap}
        onSaveArtifact={onSaveArtifact}
        onOpenArtifact={setOpenArtifact}
        seedSteps={seedSteps}
        demoUserText={demoUserText}
        demoAssistantText={demoAssistantText}
      />
      <SearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        sessions={sessions}
        onSelect={onSelectSession}
      />
      <ArtifactModal
        artifact={openArtifact}
        onClose={() => setOpenArtifact(null)}
        onRefreshed={(a) => {
          setOpenArtifact(a)
          void refreshArtifacts()
        }}
      />
    </main>
  )
}
