"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { nanoid } from "nanoid"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { decodeTaskRun } from "@/lib/tasks"
import type { Artifact, Session } from "@/lib/types"
import { ArtifactModal } from "./ArtifactModal"
import { ChatView } from "./ChatView"
import { SearchDialog } from "./SearchDialog"
import { Sidebar } from "./Sidebar"
import { ThemeToggle } from "./ThemeToggle"

type PendingTaskRun = { task_id: string; variables: Record<string, unknown> }

export function ChatShell() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialTaskRun = useMemo(
    () => decodeTaskRun(searchParams.get("taskRun")),
    [searchParams]
  )
  const [collapsed, setCollapsed] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(() => nanoid())
  const [pendingTaskRun, setPendingTaskRun] = useState<PendingTaskRun | null>(
    initialTaskRun
  )

  useEffect(() => {
    if (!initialTaskRun) return
    const params = new URLSearchParams(searchParams.toString())
    params.delete("taskRun")
    const qs = params.toString()
    router.replace(qs ? `/?${qs}` : "/")
  }, [initialTaskRun, searchParams, router])
  const [sessions, setSessions] = useState<Session[]>([])
  const [savedArtifacts, setSavedArtifacts] = useState<Artifact[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null)

  const refreshArtifacts = useCallback(async () => {
    try {
      setSavedArtifacts(await api.listArtifacts({ pinned: true }))
    } catch (e) {
      console.error("listArtifacts", e)
      toast.error("Failed to load artifacts", { description: String(e) })
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
    } catch (e) {
      console.error("listSessions", e)
      toast.error("Failed to load sessions", { description: String(e) })
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
      toast.error("Couldn't delete session", { description: String(e) })
    }
  }

  const pendingTrashRef = useRef(
    new Map<string, { undone: boolean; session: Session; index: number }>()
  )

  const onTrashSession = (id: string) => {
    const idx = sessions.findIndex((s) => s.id === id)
    if (idx < 0) return
    const session = sessions[idx]
    pendingTrashRef.current.set(id, { undone: false, session, index: idx })
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (id === activeSessionId) setActiveSessionId(nanoid())
    toast(`Deleted "${session.title || "Untitled"}"`, {
      duration: 5000,
      action: {
        label: "Undo",
        onClick: () => {
          const entry = pendingTrashRef.current.get(id)
          if (!entry) return
          entry.undone = true
          pendingTrashRef.current.delete(id)
          setSessions((prev) => {
            if (prev.some((s) => s.id === id)) return prev
            const next = [...prev]
            next.splice(Math.min(entry.index, next.length), 0, entry.session)
            return next
          })
        },
      },
      onAutoClose: () => {
        const entry = pendingTrashRef.current.get(id)
        if (!entry || entry.undone) return
        pendingTrashRef.current.delete(id)
        api.deleteSession(id).catch((e) => {
          console.error("deleteSession", e)
          toast.error("Couldn't delete session", { description: String(e) })
          void refreshSessions()
        })
      },
    })
  }

  const onRenameSession = async (id: string, title: string) => {
    try {
      await api.patchSession(id, { title })
      await refreshSessions()
    } catch (e) {
      console.error("renameSession", e)
      toast.error("Couldn't rename session", { description: String(e) })
    }
  }

  const onTogglePinSession = async (id: string, pinned: boolean) => {
    try {
      await api.patchSession(id, { is_pinned: pinned })
      await refreshSessions()
    } catch (e) {
      console.error("pinSession", e)
      toast.error("Couldn't update pin", { description: String(e) })
    }
  }

  const onDeleteArtifact = async (id: string) => {
    try {
      await api.deleteArtifact(id)
      if (openArtifact?.id === id) setOpenArtifact(null)
      await refreshArtifacts()
    } catch (e) {
      console.error("deleteArtifact", e)
      toast.error("Couldn't delete artifact", { description: String(e) })
    }
  }

  const pendingArtifactRef = useRef(
    new Map<string, { undone: boolean; artifact: Artifact; index: number }>()
  )

  const onTrashArtifact = (id: string) => {
    const idx = savedArtifacts.findIndex((a) => a.id === id)
    if (idx < 0) return
    const artifact = savedArtifacts[idx]
    pendingArtifactRef.current.set(id, { undone: false, artifact, index: idx })
    setSavedArtifacts((prev) => prev.filter((a) => a.id !== id))
    if (openArtifact?.id === id) setOpenArtifact(null)
    toast(`Deleted "${artifact.title || "Untitled"}"`, {
      duration: 5000,
      action: {
        label: "Undo",
        onClick: () => {
          const entry = pendingArtifactRef.current.get(id)
          if (!entry) return
          entry.undone = true
          pendingArtifactRef.current.delete(id)
          setSavedArtifacts((prev) => {
            if (prev.some((a) => a.id === id)) return prev
            const next = [...prev]
            next.splice(Math.min(entry.index, next.length), 0, entry.artifact)
            return next
          })
        },
      },
      onAutoClose: () => {
        const entry = pendingArtifactRef.current.get(id)
        if (!entry || entry.undone) return
        pendingArtifactRef.current.delete(id)
        api.deleteArtifact(id).catch((e) => {
          console.error("deleteArtifact", e)
          toast.error("Couldn't delete artifact", { description: String(e) })
          void refreshArtifacts()
        })
      },
    })
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
        toast.error("Couldn't create session", { description: String(e) })
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
      toast.error("Couldn't save artifact", { description: String(e) })
    }
  }

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
        onTrashSession={onTrashSession}
        onRenameSession={onRenameSession}
        onTogglePinSession={onTogglePinSession}
        artifacts={savedArtifacts}
        onOpenArtifact={setOpenArtifact}
        onDeleteArtifact={onDeleteArtifact}
        onTrashArtifact={onTrashArtifact}
      />
      <ChatView
        sessionId={activeSessionId}
        onFirstUserMessage={onFirstUserMessage}
        savedArtifacts={savedMap}
        onSaveArtifact={onSaveArtifact}
        onOpenArtifact={setOpenArtifact}
        onArtifactRefreshed={() => {
          void refreshArtifacts()
        }}
        initialTaskRun={pendingTaskRun ?? undefined}
        onTaskRunConsumed={() => {
          setPendingTaskRun(null)
          void refreshSessions()
        }}
      />
      <SearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        sessions={sessions}
        onSelect={onSelectSession}
      />
      <ArtifactModal
        artifact={openArtifact}
        saved={openArtifact ? !!savedMap[openArtifact.id] : false}
        onClose={() => setOpenArtifact(null)}
        onSaveArtifact={onSaveArtifact}
        onRefreshed={(a) => {
          setOpenArtifact(a)
          void refreshArtifacts()
        }}
      />
      <ThemeToggle />
    </main>
  )
}
