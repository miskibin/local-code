"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { nanoid } from "nanoid"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { decodeTaskRun } from "@/lib/tasks"
import type { Artifact, Session } from "@/lib/types"
import { showUndoableDelete, type UndoableEntry } from "@/lib/undoable-delete"
import { ArtifactModal } from "./ArtifactModal"
import { ChatView } from "./ChatView"
import { SearchDialog } from "./SearchDialog"
import { Sidebar } from "./Sidebar"
import { ThemeToggle } from "./ThemeToggle"

type PendingTaskRun = { task_id: string; variables: Record<string, unknown> }

export function ChatShell({ initialSessionId }: { initialSessionId: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialTaskRun = useMemo(
    () => decodeTaskRun(searchParams.get("taskRun")),
    [searchParams]
  )
  const [collapsed, setCollapsed] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(initialSessionId)
  const [pendingTaskRun, setPendingTaskRun] = useState<PendingTaskRun | null>(
    initialTaskRun
  )

  useEffect(() => {
    if (!initialTaskRun) return
    const params = new URLSearchParams(searchParams.toString())
    params.delete("taskRun")
    const qs = params.toString()
    router.replace(
      qs ? `/chat/${initialSessionId}?${qs}` : `/chat/${initialSessionId}`
    )
  }, [initialTaskRun, searchParams, router, initialSessionId])

  useEffect(() => {
    setActiveSessionId(initialSessionId)
  }, [initialSessionId])
  const [sessions, setSessions] = useState<Session[]>([])
  const [savedArtifacts, setSavedArtifacts] = useState<Artifact[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null)
  const [langfuseTraceUrl, setLangfuseTraceUrl] = useState<string | null>(null)

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
    router.push(`/chat/${nanoid()}`)
  }

  const onSelectSession = (id: string) => {
    router.push(`/chat/${id}`)
  }

  const onDeleteSession = async (id: string) => {
    try {
      await api.deleteSession(id)
      if (id === activeSessionId) router.push(`/chat/${nanoid()}`)
      await refreshSessions()
    } catch (e) {
      console.error("deleteSession", e)
      toast.error("Couldn't delete session", { description: String(e) })
    }
  }

  const pendingTrashRef = useRef(new Map<string, UndoableEntry<Session>>())

  const onTrashSession = (id: string) => {
    showUndoableDelete<Session>({
      id,
      items: sessions,
      pending: pendingTrashRef.current,
      setItems: setSessions,
      getId: (s) => s.id,
      toastTitle: (s) => `Deleted "${s.title || "Untitled"}"`,
      errorTitle: "Couldn't delete session",
      errorLogTag: "deleteSession",
      confirm: (sid) => api.deleteSession(sid),
      refresh: () => {
        void refreshSessions()
      },
      beforeShow: () => {
        if (id === activeSessionId) router.push(`/chat/${nanoid()}`)
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

  const pendingArtifactRef = useRef(new Map<string, UndoableEntry<Artifact>>())

  const onTrashArtifact = (id: string) => {
    showUndoableDelete<Artifact>({
      id,
      items: savedArtifacts,
      pending: pendingArtifactRef.current,
      setItems: setSavedArtifacts,
      getId: (a) => a.id,
      toastTitle: (a) => `Deleted "${a.title || "Untitled"}"`,
      errorTitle: "Couldn't delete artifact",
      errorLogTag: "deleteArtifact",
      confirm: (aid) => api.deleteArtifact(aid),
      refresh: () => {
        void refreshArtifacts()
      },
      beforeShow: () => {
        if (openArtifact?.id === id) setOpenArtifact(null)
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
        langfuseTraceUrl={langfuseTraceUrl}
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
        onLangfuseTraceUrlChange={setLangfuseTraceUrl}
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
