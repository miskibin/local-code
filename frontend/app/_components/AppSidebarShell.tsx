"use client"

import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { useRouter } from "next/navigation"
import { nanoid } from "nanoid"
import { toast } from "sonner"
import { api } from "@/lib/api"
import type { Artifact, Session } from "@/lib/types"
import { showUndoableDelete, type UndoableEntry } from "@/lib/undoable-delete"
import { ArtifactModal } from "./ArtifactModal"
import { SearchDialog } from "./SearchDialog"
import { Sidebar } from "./Sidebar"
import { ThemeToggle } from "./ThemeToggle"

const cache: { sessions: Session[]; artifacts: Artifact[] } = {
  sessions: [],
  artifacts: [],
}

export type AppSidebarOutlet = {
  savedArtifacts: Record<string, boolean>
  onSaveArtifact: (a: Artifact) => Promise<void> | void
  onArtifactRefreshed: () => void
  onOpenArtifact: (a: Artifact) => void
  sessions: Session[]
  refreshSessions: () => Promise<void>
}

type AppSidebarShellProps = {
  activeSessionId: string
  langfuseTraceUrl?: string | null
  children:
    | ReactNode
    | ((outlet: AppSidebarOutlet) => ReactNode)
}

export function AppSidebarShell({
  children,
  activeSessionId,
  langfuseTraceUrl = null,
}: AppSidebarShellProps) {
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const [sessions, setSessions] = useState<Session[]>(cache.sessions)
  const [savedArtifacts, setSavedArtifacts] = useState<Artifact[]>(
    cache.artifacts
  )
  const [searchOpen, setSearchOpen] = useState(false)
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null)

  const refreshArtifacts = useCallback(async () => {
    try {
      const next = await api.listArtifacts({ pinned: true })
      cache.artifacts = next
      setSavedArtifacts(next)
    } catch (e) {
      console.error("listArtifacts", e)
      toast.error("Failed to load artifacts", { description: String(e) })
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      const next = await api.listSessions()
      cache.sessions = next
      setSessions(next)
    } catch (e) {
      console.error("listSessions", e)
      toast.error("Failed to load sessions", { description: String(e) })
    }
  }, [])

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- mount load (same as prior ChatShell) */
    void refreshSessions()
    void refreshArtifacts()
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [refreshSessions, refreshArtifacts])

  useEffect(() => {
    cache.sessions = sessions
  }, [sessions])

  useEffect(() => {
    cache.artifacts = savedArtifacts
  }, [savedArtifacts])

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

  const savedMap = useMemo(() => {
    const m: Record<string, boolean> = {}
    for (const a of savedArtifacts) m[a.id] = true
    return m
  }, [savedArtifacts])

  const onSaveArtifact = useCallback(
    async (a: Artifact) => {
      try {
        await api.saveArtifact({
          ...a,
          session_id: activeSessionId || a.session_id || null,
        })
        await refreshArtifacts()
      } catch (e) {
        console.error("saveArtifact", e)
        toast.error("Couldn't save artifact", { description: String(e) })
      }
    },
    [activeSessionId, refreshArtifacts]
  )

  const outlet: AppSidebarOutlet = useMemo(
    () => ({
      savedArtifacts: savedMap,
      onSaveArtifact,
      onArtifactRefreshed: () => {
        void refreshArtifacts()
      },
      onOpenArtifact: setOpenArtifact,
      sessions,
      refreshSessions,
    }),
    [savedMap, onSaveArtifact, refreshArtifacts, sessions, refreshSessions]
  )

  const body =
    typeof children === "function" ? children(outlet) : children

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
      {body}
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
