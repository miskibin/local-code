"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { decodeTaskRun } from "@/lib/tasks"
import { AppSidebarShell } from "./AppSidebarShell"
import { ChatView } from "./ChatView"

type PendingTaskRun = { task_id: string; variables: Record<string, unknown> }

export function ChatShell({ initialSessionId }: { initialSessionId: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const initialTaskRun = useMemo(
    () => decodeTaskRun(searchParams.get("taskRun")),
    [searchParams]
  )
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
    /* eslint-disable react-hooks/set-state-in-effect -- sync active thread from URL */
    setActiveSessionId(initialSessionId)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [initialSessionId])

  const [langfuseTraceUrl, setLangfuseTraceUrl] = useState<string | null>(null)

  return (
    <AppSidebarShell
      activeSessionId={activeSessionId}
      langfuseTraceUrl={langfuseTraceUrl}
    >
      {(outlet) => {
        const isTaskChat =
          !!pendingTaskRun ||
          !!outlet.sessions.find((s) => s.id === activeSessionId)?.task_id

        const onFirstUserMessage = async (text: string) => {
          const exists = outlet.sessions.some((s) => s.id === activeSessionId)
          if (exists) return
          try {
            await api.createSession({
              id: activeSessionId,
              title: text.slice(0, 40) || "Untitled",
            })
            await outlet.refreshSessions()
          } catch (e) {
            console.error("createSession", e)
            toast.error("Couldn't create session", { description: String(e) })
          }
        }

        return (
          <ChatView
            sessionId={activeSessionId}
            isTaskChat={isTaskChat}
            onFirstUserMessage={onFirstUserMessage}
            savedArtifacts={outlet.savedArtifacts}
            onSaveArtifact={outlet.onSaveArtifact}
            onOpenArtifact={outlet.onOpenArtifact}
            onArtifactRefreshed={outlet.onArtifactRefreshed}
            initialTaskRun={pendingTaskRun ?? undefined}
            onTaskRunConsumed={() => {
              setPendingTaskRun(null)
              void outlet.refreshSessions()
            }}
            onLangfuseTraceUrlChange={setLangfuseTraceUrl}
          />
        )
      }}
    </AppSidebarShell>
  )
}
