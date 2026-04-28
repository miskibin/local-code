"use client"

import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"
import { api, CHAT_URL } from "@/lib/api"
import { authHeaders } from "@/lib/auth"
import type { Artifact, SubagentStep, Todo, ToolStep } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Composer } from "./Composer"
import { EmptyState } from "./EmptyState"
import {
  AssistantMessage,
  contentBlocksToPlainText,
  UserMessage,
} from "./Messages"
import type { AssistantMsg, ContentBlock, UserAttachment } from "./Messages"
import { GeneratingTaskModal } from "./tasks/GeneratingTaskModal"
import {
  ArtifactRefsProvider,
  type ArtifactRefs,
  type ToolArtifactRef,
} from "./ArtifactRefs"

const DEFAULT_MODEL =
  process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "gemini-3.1-flash-lite-preview"

export type AnyPart = {
  type: string
  text?: string
  toolCallId?: string
  toolName?: string
  state?: string
  input?: unknown
  output?: unknown
  errorText?: string
  data?: unknown
  id?: string
  callProviderMetadata?: Record<string, Record<string, unknown>>
  resultProviderMetadata?: Record<string, Record<string, unknown>>
}

export type ArtifactDataPart = {
  toolCallId: string
  artifactId: string
  kind: "table" | "image" | "text" | "pptx"
  title: string
  summary: string
  updatedAt: string
}

export type UsageDataPart = {
  inputTokens: number
  outputTokens: number
  durationMs?: number
  contextMaxTokens?: number
  modelId?: string
}

function extractSummaryFired(parts: AnyPart[]): boolean {
  for (const p of parts) {
    if (p.type === "data-summary") return true
  }
  return false
}

function extractUsage(parts: AnyPart[]): UsageDataPart | null {
  for (let i = parts.length - 1; i >= 0; i--) {
    const p = parts[i]
    if (p.type !== "data-usage") continue
    const d = p.data as UsageDataPart | undefined
    if (!d) continue
    return d
  }
  return null
}

export type TraceDataPart = {
  traceId: string
  messageId?: string
  traceUrl?: string
  feedback?: 0 | 1
}

function extractTrace(parts: AnyPart[]): TraceDataPart | null {
  for (let i = parts.length - 1; i >= 0; i--) {
    const p = parts[i]
    if (p.type !== "data-trace") continue
    const d = p.data as TraceDataPart | undefined
    if (!d?.traceId) continue
    return d
  }
  return null
}

export function extractArtifactIds(parts: AnyPart[]): string[] {
  const out: string[] = []
  for (const p of parts) {
    if (p.type !== "data-artifact") continue
    const data = p.data as ArtifactDataPart | undefined
    if (data?.artifactId) out.push(data.artifactId)
  }
  return out
}

function getParentToolCallId(p: AnyPart): string | null {
  const sub =
    (p.resultProviderMetadata?.subagent as
      | Record<string, unknown>
      | undefined) ??
    (p.callProviderMetadata?.subagent as Record<string, unknown> | undefined)
  const parent = sub?.parentToolCallId
  return typeof parent === "string" ? parent : null
}

function isToolPart(p: AnyPart): boolean {
  return p.type === "dynamic-tool" || p.type.startsWith("tool-")
}

function getToolName(p: AnyPart): string | null {
  if (p.type === "dynamic-tool") return p.toolName ?? null
  if (p.type.startsWith("tool-")) return p.type.slice(5)
  return null
}

function extractTodos(p: AnyPart): Todo[] | null {
  if (getToolName(p) !== "write_todos") return null
  const input = p.input as { todos?: unknown } | undefined
  if (!input || !Array.isArray(input.todos) || input.todos.length === 0) {
    return null
  }
  const todos: Todo[] = []
  for (const t of input.todos) {
    if (typeof t !== "object" || t === null) continue
    const obj = t as { content?: unknown; status?: unknown }
    const content = typeof obj.content === "string" ? obj.content : ""
    const status: Todo["status"] =
      obj.status === "completed" || obj.status === "in_progress"
        ? obj.status
        : "pending"
    todos.push({ content, status })
  }
  return todos.length > 0 ? todos : null
}

function prettifyAgentName(id: string): string {
  return id
    .split(/[-_]/)
    .filter(Boolean)
    .map((s) => s[0].toUpperCase() + s.slice(1))
    .join(" ")
}

function getTaskTitle(p: AnyPart): string | undefined {
  const task =
    (p.callProviderMetadata?.task as Record<string, unknown> | undefined) ??
    (p.resultProviderMetadata?.task as Record<string, unknown> | undefined)
  const title = task?.title
  return typeof title === "string" ? title : undefined
}

function getTaskId(p: AnyPart): string | undefined {
  const task =
    (p.callProviderMetadata?.task as Record<string, unknown> | undefined) ??
    (p.resultProviderMetadata?.task as Record<string, unknown> | undefined)
  const id = task?.taskId
  return typeof id === "string" ? id : undefined
}

function partToToolStep(p: AnyPart): ToolStep | null {
  let toolName: string | null = null
  if (p.type === "dynamic-tool") toolName = p.toolName ?? null
  else if (p.type.startsWith("tool-")) toolName = p.type.slice(5)
  if (!toolName) return null
  const state = p.state ?? "input-available"
  const status: ToolStep["status"] =
    state === "output-available"
      ? "done"
      : state === "output-error"
        ? "error"
        : "running"
  let result = ""
  if (state === "output-available")
    result =
      typeof p.output === "string" ? p.output : JSON.stringify(p.output ?? "")
  else if (state === "output-error") result = p.errorText ?? "error"
  else result = "…"
  const server = toolName.includes("_") ? toolName.split("_")[0] : "local"
  const args =
    typeof p.input === "object" && p.input !== null
      ? (p.input as Record<string, unknown>)
      : { _input: p.input }
  return {
    kind: "tool",
    tool: toolName,
    server,
    args,
    result,
    status,
    toolCallId: p.toolCallId,
    taskTitle: getTaskTitle(p),
    taskId: getTaskId(p),
  }
}

/**
 * Builds a tree of content blocks from raw parts:
 *  - text parts become text blocks
 *  - tool parts whose providerMetadata.subagent.parentToolCallId points at
 *    another tool become children of that tool, which is rendered as a
 *    SubagentStep with a nested step list
 *  - `write_todos` tool calls collapse into a single plan block at the
 *    position of the first call, using the latest todos as state of truth
 *  - all other tool parts render as plain ToolSteps
 *
 * Order matches the stream — children always appear inside their parent's
 * SubagentStep regardless of where they fell in the part array.
 */
function extractEmailDraftBlock(
  p: AnyPart
): Extract<ContentBlock, { type: "email_draft" }> | null {
  if (getToolName(p) !== "email_draft" || !p.toolCallId) return null
  const input = (p.input ?? {}) as {
    to?: unknown
    subject?: unknown
    body?: unknown
    cc?: unknown
    bcc?: unknown
    attachment_artifact_ids?: unknown
  }
  const asStr = (v: unknown) => (typeof v === "string" ? v : "")
  const asStrList = (v: unknown) =>
    Array.isArray(v) ? v.filter((s): s is string => typeof s === "string") : []
  const state = p.state ?? "input-available"
  const status: "running" | "done" | "error" =
    state === "output-available"
      ? "done"
      : state === "output-error"
        ? "error"
        : "running"
  return {
    type: "email_draft",
    toolCallId: p.toolCallId,
    to: asStr(input.to),
    subject: asStr(input.subject),
    body: asStr(input.body),
    cc: asStrList(input.cc),
    bcc: asStrList(input.bcc),
    attachmentArtifactIds: asStrList(input.attachment_artifact_ids),
    status,
  }
}

function extractQuizBlock(
  p: AnyPart
): Extract<ContentBlock, { type: "quiz" }> | null {
  if (getToolName(p) !== "quiz" || !p.toolCallId) return null
  const input = (p.input ?? {}) as {
    question?: unknown
    options?: unknown
    allow_custom?: unknown
  }
  const question = typeof input.question === "string" ? input.question : ""
  const options = Array.isArray(input.options)
    ? input.options.filter((o): o is string => typeof o === "string")
    : []
  const allowCustom = input.allow_custom !== false
  const state = p.state ?? "input-available"
  const status: "running" | "done" | "error" =
    state === "output-available"
      ? "done"
      : state === "output-error"
        ? "error"
        : "running"
  const answer =
    state === "output-available" && typeof p.output === "string"
      ? p.output
      : undefined
  return {
    type: "quiz",
    toolCallId: p.toolCallId,
    question,
    options,
    allowCustom,
    status,
    answer,
  }
}

type PartsToContentBlocksOpts = {
  /** When false, the resolved plan block is suppressed (write_todos parts
   * are still skipped from raw rendering). Used to dedupe across multiple
   * assistant messages — only one survives. Defaults to true. */
  emitPlan?: boolean
  /** When provided alongside emitPlan, render this todos list instead of
   * the local latest. Used to surface the cumulative latest plan state on
   * the surviving message. */
  overrideTodos?: Todo[]
  /** Paired with overrideTodos. */
  overrideStreaming?: boolean
}

function partsToContentBlocks(
  parts: AnyPart[],
  opts: PartsToContentBlocksOpts = {}
): ContentBlock[] {
  const emitPlan = opts.emitPlan !== false
  // Pass 1 — collect every tool part keyed by its toolCallId, plus its parent
  // link if any.
  const stepByCallId = new Map<string, ToolStep>()
  const partByCallId = new Map<string, AnyPart>()
  const parentOf = new Map<string, string>()
  const childrenOf = new Map<string, string[]>()

  for (const p of parts) {
    if (!isToolPart(p) || !p.toolCallId) continue
    const step = partToToolStep(p)
    if (!step) continue
    stepByCallId.set(p.toolCallId, step)
    partByCallId.set(p.toolCallId, p)
    const parent = getParentToolCallId(p)
    if (parent) {
      parentOf.set(p.toolCallId, parent)
      const arr = childrenOf.get(parent) ?? []
      arr.push(p.toolCallId)
      childrenOf.set(parent, arr)
    }
  }

  if (process.env.NEXT_PUBLIC_DEBUG === "1") {
    for (const [child, parent] of parentOf) {
      if (!stepByCallId.has(parent)) {
        console.debug("[chat] orphan tool parent", { child, parent })
      }
    }
  }

  // Pass 1.5 — collect `write_todos` state. The agent calls it repeatedly to
  // mutate statuses; each call replaces the entire list. We render a single
  // plan block, using the latest non-empty todos. Streaming = latest call's
  // output hasn't arrived. write_todos is excluded from subagent tool rosters
  // (see backend/app/graphs/main_agent.py) so every call is top-level — no
  // anchor traversal needed.
  let firstWriteTodosCallId: string | null = null
  let latestTodos: Todo[] | null = null
  let latestWriteTodosState: string | undefined
  const writeTodosCallIds = new Set<string>()
  for (const p of parts) {
    if (getToolName(p) !== "write_todos" || !p.toolCallId) continue
    writeTodosCallIds.add(p.toolCallId)
    if (firstWriteTodosCallId === null) firstWriteTodosCallId = p.toolCallId
    const todos = extractTodos(p)
    if (todos) {
      latestTodos = todos
      latestWriteTodosState = p.state
    }
  }
  const planStreaming = latestWriteTodosState
    ? latestWriteTodosState !== "output-available" &&
      latestWriteTodosState !== "output-error"
    : false
  const planAnchorCallId: string | null = firstWriteTodosCallId
  const renderTodos = opts.overrideTodos ?? latestTodos
  const renderStreaming = opts.overrideTodos
    ? (opts.overrideStreaming ?? false)
    : planStreaming

  // Pass 2 — walk parts in stream order. Skip tool parts that have a known
  // parent (they're rendered as nested children below). Group children whose
  // parent has any sub-tools into a SubagentStep.
  const out: ContentBlock[] = []
  let textAcc = ""
  const flush = () => {
    if (textAcc.length > 0) {
      out.push({ type: "text", text: textAcc })
      textAcc = ""
    }
  }

  let planEmitted = false
  const emitPlanIfAnchor = (callId: string) => {
    if (planEmitted) return
    if (!emitPlan) return
    if (callId !== planAnchorCallId) return
    if (!renderTodos) return
    flush()
    out.push({
      type: "plan",
      todos: renderTodos,
      streaming: renderStreaming,
    })
    planEmitted = true
  }

  for (const p of parts) {
    if (p.type === "text") {
      textAcc += p.text ?? ""
      continue
    }
    if (!isToolPart(p) || !p.toolCallId) continue

    // write_todos parts are collapsed into the single plan block. Emit the
    // plan here only when this part is itself the resolved anchor (i.e., a
    // top-level write_todos with no subagent parent).
    if (writeTodosCallIds.has(p.toolCallId)) {
      emitPlanIfAnchor(p.toolCallId)
      continue
    }

    // Quiz blocks render as their own user-facing card, even when emitted
    // from inside a subagent — they need to be prominent for the user to
    // answer.
    if (getToolName(p) === "quiz") {
      const quiz = extractQuizBlock(p)
      if (quiz) {
        // Ghost quiz parts can appear in the new assistant message during a
        // resume turn (the tool-output flows into a fresh msg with no input).
        // Skip rendering until the post-stream refetch reconciles state.
        if (quiz.question) {
          flush()
          out.push(quiz)
        }
        continue
      }
    }

    if (getToolName(p) === "email_draft") {
      const draft = extractEmailDraftBlock(p)
      if (draft) {
        if (draft.to || draft.subject || draft.body) {
          flush()
          out.push(draft)
        }
        continue
      }
    }

    // Has a parent that we know about → consumed by parent's SubagentStep.
    const parentId = parentOf.get(p.toolCallId)
    if (parentId && stepByCallId.has(parentId)) continue

    emitPlanIfAnchor(p.toolCallId)
    flush()
    const childIds = childrenOf.get(p.toolCallId) ?? []
    const ownStep = stepByCallId.get(p.toolCallId)!
    if (childIds.length === 0) {
      out.push({ type: "step", step: ownStep })
    } else {
      out.push({
        type: "step",
        step: buildSubagentStep(ownStep, childIds, stepByCallId),
      })
    }
  }
  flush()
  return out
}

function buildSubagentStep(
  parent: ToolStep,
  childIds: string[],
  stepByCallId: Map<string, ToolStep>
): SubagentStep {
  const args = parent.args ?? {}
  const subagentType =
    typeof args.subagent_type === "string" ? args.subagent_type : "subagent"
  const description =
    typeof args.description === "string" ? args.description : parent.tool
  const children: ToolStep[] = []
  for (const cid of childIds) {
    const s = stepByCallId.get(cid)
    if (s) children.push(s)
  }
  return {
    kind: "subagent",
    agent: { id: subagentType, name: prettifyAgentName(subagentType) },
    task: description,
    status: parent.status,
    steps: children,
    summary:
      parent.status === "done" && parent.result && parent.result !== "…"
        ? parent.result
        : undefined,
  }
}

function partsToText(parts: AnyPart[]): string {
  return parts
    .filter((p) => p.type === "text")
    .map((p) => p.text ?? "")
    .join("")
}

export const __testing__ = {
  partsToContentBlocks,
  extractArtifactIds,
  extractUsage,
}

type Props = {
  sessionId: string
  isTaskChat?: boolean
  onFirstUserMessage: (text: string) => void
  savedArtifacts: Record<string, boolean>
  onSaveArtifact: (a: Artifact) => Promise<void> | void
  onOpenArtifact: (a: Artifact) => void
  /** After an inline table refresh; use to sync saved-artifact list. */
  onArtifactRefreshed?: (a: Artifact) => void
  initialTaskRun?: { task_id: string; variables: Record<string, unknown> }
  onTaskRunConsumed?: () => void
  /** Latest assistant `data-trace` URL in this thread (for sidebar Langfuse link). */
  onLangfuseTraceUrlChange?: (url: string | null) => void
}

export function ChatView({
  sessionId,
  isTaskChat = false,
  onFirstUserMessage,
  savedArtifacts,
  onSaveArtifact,
  onOpenArtifact,
  onArtifactRefreshed,
  initialTaskRun,
  onTaskRunConsumed,
  onLangfuseTraceUrlChange,
}: Props) {
  const router = useRouter()
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL)
  const [generatingTask, setGeneratingTask] = useState(false)
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: CHAT_URL,
        headers: () => authHeaders(),
        prepareSendMessagesRequest: ({ id, messages, body, trigger }) => {
          const b = body as
            | {
                reset?: boolean
                model?: string
                task_run?: {
                  task_id: string
                  variables: Record<string, unknown>
                }
                resume?: { toolCallId: string; value: string }
              }
            | undefined
          // Strip placeholder user messages used to drive resume turns; the
          // backend reads `resume` and ignores `messages` in that case.
          const cleanMessages = messages.filter(
            (m) =>
              !(
                m.role === "user" &&
                (m.parts ?? []).some(
                  (p) =>
                    p.type === "text" &&
                    (p as { text: string }).text === "__resume__"
                )
              )
          )
          const attachments = pendingAttachmentsRef.current
          pendingAttachmentsRef.current = []
          const lastUserIdx = (() => {
            for (let i = cleanMessages.length - 1; i >= 0; i--) {
              if (cleanMessages[i].role === "user") return i
            }
            return -1
          })()
          return {
            body: {
              id,
              messages: cleanMessages.map((m, idx) => {
                const textParts = (m.parts ?? [])
                  .filter((p) => p.type === "text")
                  .map((p) => ({
                    type: "text" as const,
                    text: (p as { text: string }).text,
                  }))
                const fileParts =
                  idx === lastUserIdx && attachments.length > 0
                    ? attachments.map((a) => ({
                        type: "file" as const,
                        artifactId: a.id,
                        mediaType:
                          (a.payload as { mime?: string } | undefined)?.mime ??
                          (a.kind === "image"
                            ? "image/png"
                            : a.kind === "table"
                              ? "text/csv"
                              : "text/plain"),
                        name: a.title,
                      }))
                    : []
                return {
                  id: m.id,
                  role: m.role,
                  parts: [...textParts, ...fileParts],
                }
              }),
              reset: trigger === "regenerate-message" || b?.reset === true,
              model: b?.model ?? selectedModel,
              ...(b?.task_run ? { task_run: b.task_run } : {}),
              ...(b?.resume ? { resume: b.resume } : {}),
            },
          }
        },
      }),
    [selectedModel]
  )
  const [streamFault, setStreamFault] = useState<
    "incomplete" | "unreachable" | null
  >(null)
  const messagesRef = useRef<{ role: string }[]>([])
  const resumePendingRef = useRef(false)
  const pendingAttachmentsRef = useRef<Artifact[]>([])
  const [userAttachments, setUserAttachments] = useState<
    Record<string, UserAttachment[]>
  >({})
  const { messages, sendMessage, regenerate, setMessages, status, stop } =
    useChat({
      id: sessionId,
      transport,
      onFinish: () => {
        if (!resumePendingRef.current) return
        resumePendingRef.current = false
        api
          .getMessages(sessionId)
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .then((m) => setMessages(m as any))
          .catch(() => {})
      },
      onError: (e) => {
        const msg = e?.message ?? ""
        const isNetwork =
          e instanceof TypeError ||
          /failed to fetch|networkerror|fetch/i.test(msg)
        if (isNetwork) {
          setStreamFault("unreachable")
          toast.error("Can't reach backend", { description: msg })
          return
        }
        const last = messagesRef.current[messagesRef.current.length - 1]
        if (last?.role === "assistant") {
          setStreamFault("incomplete")
          return
        }
        toast.error(msg || "Stream error")
      },
    })
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [artifactCache, setArtifactCache] = useState<Record<string, Artifact>>(
    {}
  )
  const scrollRef = useRef<HTMLDivElement>(null)
  const sentFirstRef = useRef(false)
  const [loadingHistory, setLoadingHistory] = useState(true)

  const streaming = status === "streaming" || status === "submitted"

  useEffect(() => {
    setExpanded({})
    sentFirstRef.current = false
    setLoadingHistory(true)
    let cancelled = false
    api
      .getMessages(sessionId)
      .then((m) => {
        if (cancelled) return
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setMessages(m as any)
        if (m.length > 0) sentFirstRef.current = true
      })
      .catch(() => {
        if (!cancelled) setMessages([])
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, setMessages])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    const allIds = new Set<string>()
    for (const m of messages) {
      for (const id of extractArtifactIds((m.parts ?? []) as AnyPart[])) {
        allIds.add(id)
      }
    }
    const missing = Array.from(allIds).filter((id) => !artifactCache[id])
    if (missing.length === 0) return
    let cancelled = false
    Promise.all(
      missing.map((id) =>
        api.getArtifact(id).then(
          (a) => [id, a] as const,
          () => null
        )
      )
    ).then((results) => {
      if (cancelled) return
      setArtifactCache((prev) => {
        const next = { ...prev }
        for (const r of results) {
          if (r) next[r[0]] = r[1]
        }
        return next
      })
    })
    return () => {
      cancelled = true
    }
  }, [messages, artifactCache])

  useEffect(() => {
    if (sentFirstRef.current) return
    const firstUser = messages.find((m) => m.role === "user")
    if (!firstUser) return
    const text = firstUser.parts
      .filter((p) => p.type === "text")
      .map((p) => (p as { text: string }).text)
      .join("")
    if (text) {
      sentFirstRef.current = true
      onFirstUserMessage(text)
    }
  }, [messages, onFirstUserMessage])

  const toolArtifactMap = useMemo(() => {
    const m: Record<string, ToolArtifactRef> = {}
    for (const msg of messages) {
      for (const p of (msg.parts ?? []) as AnyPart[]) {
        if (p.type !== "data-artifact") continue
        const data = p.data as ArtifactDataPart | undefined
        if (data?.toolCallId && data?.artifactId) {
          m[data.toolCallId] = {
            artifactId: data.artifactId,
            kind: data.kind,
            title: data.title,
          }
        }
      }
    }
    return m
  }, [messages])

  const artifactRefs = useMemo<ArtifactRefs>(
    () => ({
      getArtifact: (id) => artifactCache[id],
      getToolArtifact: (cid) => toolArtifactMap[cid],
      isSaved: (id) => !!savedArtifacts[id],
      onSave: (a) => void onSaveArtifact(a),
      onOpen: (id) => {
        const cached = artifactCache[id]
        if (cached) {
          onOpenArtifact(cached)
          return
        }
        void api
          .getArtifact(id)
          .then((a) => {
            setArtifactCache((prev) => ({ ...prev, [id]: a }))
            onOpenArtifact(a)
          })
          .catch((e) => {
            toast.error("Failed to open artifact", { description: String(e) })
          })
      },
      onTableRefresh: async (a) => {
        const fresh = await api.refreshArtifact(a.id)
        setArtifactCache((prev) => ({ ...prev, [a.id]: fresh }))
        onArtifactRefreshed?.(fresh)
        return fresh
      },
    }),
    [
      artifactCache,
      toolArtifactMap,
      onOpenArtifact,
      onArtifactRefreshed,
      savedArtifacts,
      onSaveArtifact,
    ]
  )

  const toggleStep = (key: string) =>
    setExpanded((p) => ({ ...p, [key]: !p[key] }))

  const isEmpty = messages.length === 0

  const send = (text: string, attachments: Artifact[] = []) => {
    setStreamFault(null)
    pendingAttachmentsRef.current = attachments
    if (attachments.length > 0) {
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `m_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
      const ua: UserAttachment[] = attachments.map((a) => ({
        artifactId: a.id,
        mediaType:
          (a.payload as { mime?: string } | undefined)?.mime ??
          (a.kind === "image"
            ? "image/png"
            : a.kind === "table"
              ? "text/csv"
              : "text/plain"),
        name: a.title,
      }))
      setUserAttachments((prev) => ({ ...prev, [id]: ua }))
      setArtifactCache((prev) => {
        const next = { ...prev }
        for (const a of attachments) next[a.id] = a
        return next
      })
      sendMessage({
        id,
        role: "user",
        parts: [{ type: "text", text }],
      })
    } else {
      sendMessage({ text })
    }
  }

  const submitQuizAnswer = (toolCallId: string, value: string) => {
    setStreamFault(null)
    resumePendingRef.current = true
    sendMessage(
      { text: "__resume__" },
      { body: { resume: { toolCallId, value } } }
    )
  }

  const pendingQuiz = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      if (m.role !== "assistant") continue
      for (const p of (m.parts ?? []) as AnyPart[]) {
        if (getToolName(p) !== "quiz") continue
        const state = p.state ?? "input-available"
        if (state === "output-available" || state === "output-error") continue
        // Match the renderer's filter: a quiz block with no question is a
        // ghost part (e.g. a stale tool-input event) and would never produce
        // a visible card. Treating it as pending would lock the composer
        // with nothing to answer.
        const input = (p.input ?? {}) as { question?: unknown }
        if (typeof input.question !== "string" || input.question.length === 0) {
          continue
        }
        return true
      }
      break
    }
    return false
  }, [messages])

  const handleEdit = (userId: string, newText: string) => {
    const idx = messages.findIndex((m) => m.id === userId)
    if (idx < 0) return
    setStreamFault(null)
    setMessages((prev) => prev.slice(0, idx))
    sendMessage({ text: newText }, { body: { reset: true } })
  }

  const retryStreamFault = () => {
    setStreamFault(null)
    if (lastAssistantId) {
      void regenerate({ messageId: lastAssistantId })
      return
    }
    const lastUser = [...messages].reverse().find((m) => m.role === "user")
    if (!lastUser) return
    const text = lastUser.parts
      .filter((p) => p.type === "text")
      .map((p) => (p as { text: string }).text)
      .join("")
    if (text) sendMessage({ text })
  }

  const handleSaveAsTask = async () => {
    if (generatingTask) return
    setGeneratingTask(true)
    try {
      const task = await api.generateTask(sessionId, selectedModel)
      router.push(`/tasks/${task.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to generate task")
    } finally {
      setGeneratingTask(false)
    }
  }

  const taskRunSentRef = useRef(false)
  useEffect(() => {
    if (!initialTaskRun) return
    if (taskRunSentRef.current) return
    if (status !== "ready") return
    taskRunSentRef.current = true
    // Backend already created ChatSession with the task title in
    // persist_run_messages — skip the auto-title flow on first user msg.
    sentFirstRef.current = true
    sendMessage(
      { text: `Run task ${initialTaskRun.task_id}` },
      { body: { reset: true, task_run: initialTaskRun } }
    )
    onTaskRunConsumed?.()
  }, [initialTaskRun, status, sendMessage, onTaskRunConsumed])

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i].id
    }
    return null
  }, [messages])

  // Cross-message plan dedup. The agent calls `write_todos` across multiple
  // assistant turns to tick statuses; each turn becomes its own message and
  // would otherwise emit its own plan card. Resolve the cumulative latest
  // plan state and the surviving message — the one that actually renders the
  // PlanCard.
  const planState = useMemo<{
    planMessageId: string | null
    todos: Todo[] | null
    streaming: boolean
  }>(() => {
    let planMessageId: string | null = null
    let todos: Todo[] | null = null
    let streaming = false
    for (const m of messages) {
      if (m.role !== "assistant") continue
      const parts = (m.parts ?? []) as AnyPart[]
      let touched = false
      for (const p of parts) {
        if (getToolName(p) !== "write_todos") continue
        touched = true
        const t = extractTodos(p)
        if (t) {
          todos = t
          const state = p.state
          streaming =
            !!state && state !== "output-available" && state !== "output-error"
        }
      }
      if (touched) planMessageId = m.id
    }
    return { planMessageId, todos, streaming }
  }, [messages])

  const latestUsage = useMemo<UsageDataPart | undefined>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      if (m.role !== "assistant") continue
      const u = extractUsage((m.parts ?? []) as AnyPart[])
      if (u) return u
    }
    return undefined
  }, [messages])

  const latestLangfuseTraceUrl = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      if (m.role !== "assistant") continue
      const url = extractTrace((m.parts ?? []) as AnyPart[])?.traceUrl
      if (url) return url
    }
    return null
  }, [messages])

  useEffect(() => {
    onLangfuseTraceUrlChange?.(latestLangfuseTraceUrl)
  }, [latestLangfuseTraceUrl, onLangfuseTraceUrlChange])

  return (
    <ArtifactRefsProvider value={artifactRefs}>
      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col",
          isTaskChat && "lc-login-bg relative"
        )}
        style={isTaskChat ? undefined : { background: "var(--bg)" }}
      >
        <div ref={scrollRef} className="lc-scroll flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-4xl px-6 pt-8 pb-12">
            {isEmpty && loadingHistory ? (
              <div className="flex h-full min-h-[60vh] items-center justify-center">
                <div
                  className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent opacity-40"
                  style={{ color: "var(--fg)" }}
                />
              </div>
            ) : isEmpty ? (
              <EmptyState onPick={send} />
            ) : (
              <div>
                {messages.map((m) => {
                  const parts = (m.parts ?? []) as AnyPart[]
                  const text = partsToText(parts)
                  if (m.role === "user") {
                    if (text === "__resume__") return null
                    return (
                      <UserMessage
                        key={m.id}
                        text={text}
                        attachments={userAttachments[m.id]}
                        onOpenAttachment={artifactRefs.onOpen}
                        onEdit={
                          streaming
                            ? undefined
                            : (newText) => handleEdit(m.id, newText)
                        }
                      />
                    )
                  }
                  const isLast = m.id === lastAssistantId
                  const isPlanCarrier = m.id === planState.planMessageId
                  const contentBlocks = partsToContentBlocks(parts, {
                    emitPlan: isPlanCarrier,
                    overrideTodos: isPlanCarrier
                      ? (planState.todos ?? undefined)
                      : undefined,
                    overrideStreaming: isPlanCarrier
                      ? planState.streaming
                      : undefined,
                  })
                  const liveArtifacts = extractArtifactIds(parts)
                    .map((id) => artifactCache[id])
                    .filter((a): a is Artifact => !!a)
                  const usage = extractUsage(parts) ?? undefined
                  const summaryFired = extractSummaryFired(parts)
                  const trace = extractTrace(parts)
                  const traceId = trace?.traceId
                  const msg: AssistantMsg = {
                    id: m.id,
                    contentBlocks,
                    artifacts:
                      liveArtifacts.length > 0 ? liveArtifacts : undefined,
                    usage,
                    summaryFired,
                    traceId,
                    initialFeedback: trace?.feedback,
                  }
                  return (
                    <AssistantMessage
                      key={m.id}
                      msg={msg}
                      expanded={expanded}
                      toggleStep={toggleStep}
                      isLast={isLast}
                      streaming={streaming && isLast}
                      savedArtifacts={savedArtifacts}
                      onSaveArtifact={(a) => void onSaveArtifact(a)}
                      onOpenArtifact={onOpenArtifact}
                      onCopy={() =>
                        void navigator.clipboard?.writeText(
                          contentBlocksToPlainText(msg.contentBlocks)
                        )
                      }
                      onSaveAsTask={
                        streaming || isTaskChat
                          ? undefined
                          : () => void handleSaveAsTask()
                      }
                      saveAsTaskBusy={generatingTask}
                      onQuizAnswer={submitQuizAnswer}
                      onFeedback={
                        traceId
                          ? (value) => void api.postFeedback(traceId, value)
                          : undefined
                      }
                    />
                  )
                })}
              </div>
            )}
          </div>
        </div>
        <div
          style={{
            background:
              "linear-gradient(to top, var(--bg), color-mix(in srgb, var(--bg) 0%, transparent))",
          }}
        >
          {streamFault && !streaming ? (
            <div className="mx-auto w-full max-w-4xl px-6 pt-2">
              <div
                className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-[13px]"
                style={{
                  background:
                    streamFault === "incomplete"
                      ? "var(--amber-soft)"
                      : "var(--red-soft)",
                  borderColor:
                    streamFault === "incomplete"
                      ? "var(--amber)"
                      : "var(--red)",
                  color:
                    streamFault === "incomplete"
                      ? "var(--amber)"
                      : "var(--red)",
                }}
              >
                <span>
                  {streamFault === "incomplete"
                    ? "Response may be incomplete."
                    : "Can't reach backend."}
                </span>
                <button
                  type="button"
                  onClick={retryStreamFault}
                  className="rounded px-2 py-1 font-medium underline-offset-2 hover:underline"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : null}
          <Composer
            onSend={send}
            onStop={() => stop()}
            streaming={streaming || pendingQuiz}
            model={selectedModel}
            onModelChange={setSelectedModel}
            sessionId={sessionId}
            usage={latestUsage}
          />
        </div>
        <GeneratingTaskModal open={generatingTask} />
      </div>
    </ArtifactRefsProvider>
  )
}
