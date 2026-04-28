import { authHeaders } from "./auth"
import type {
  Artifact,
  MCPServer,
  SavedTask,
  Session,
  SessionPatch,
  Skill,
  SkillContent,
  StoredMessage,
  TaskListItem,
  Tool,
} from "./types"

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL_BASE ?? "http://localhost:8000"

async function jsonFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const { json, ...rest } = init ?? {}
  const r = await fetch(`${BACKEND}${path}`, {
    ...rest,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
      ...(rest.headers ?? {}),
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`)
  if (r.status === 204) return undefined as T
  const ct = r.headers.get("content-type") ?? ""
  if (!ct.includes("application/json")) return undefined as T
  return (await r.json()) as T
}

export const api = {
  // Sessions
  listSessions: () => jsonFetch<Session[]>("/sessions"),
  createSession: (s: Session) =>
    jsonFetch<Session>("/sessions", { method: "POST", json: s }),
  deleteSession: (id: string) =>
    jsonFetch<{ deleted: string }>(`/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  patchSession: (id: string, patch: SessionPatch) =>
    jsonFetch<Session>(`/sessions/${encodeURIComponent(id)}`, {
      method: "PATCH",
      json: patch,
    }),
  getMessages: (id: string) =>
    jsonFetch<StoredMessage[]>(`/sessions/${encodeURIComponent(id)}/messages`),

  // Feedback
  postFeedback: (traceId: string, value: 0 | 1, comment?: string) =>
    jsonFetch<{ ok: boolean }>("/feedback", {
      method: "POST",
      json: { traceId, value, comment },
    }),

  // Tools
  listTools: () => jsonFetch<Tool[]>("/tools"),
  setTool: (name: string, enabled: boolean) =>
    jsonFetch<Tool>(`/tools/${encodeURIComponent(name)}`, {
      method: "PATCH",
      json: { enabled },
    }),

  // Skills
  listSkills: () => jsonFetch<Skill[]>("/skills"),
  setSkill: (name: string, enabled: boolean) =>
    jsonFetch<Skill>(`/skills/${encodeURIComponent(name)}`, {
      method: "PATCH",
      json: { enabled },
    }),
  getSkillContent: (name: string) =>
    jsonFetch<SkillContent>(
      `/skills/${encodeURIComponent(name)}/content`
    ),

  // MCP
  listMCP: () => jsonFetch<MCPServer[]>("/mcp"),
  upsertMCP: (s: MCPServer) =>
    jsonFetch<MCPServer>("/mcp", { method: "POST", json: s }),
  deleteMCP: (name: string) =>
    jsonFetch<{ deleted: string }>(`/mcp/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

  // Artifacts
  listArtifacts: (opts?: { pinned?: boolean }) => {
    const qs =
      opts?.pinned !== undefined
        ? `?pinned=${opts.pinned ? "true" : "false"}`
        : ""
    return jsonFetch<Artifact[]>(`/artifacts${qs}`)
  },
  getArtifact: (id: string) =>
    jsonFetch<Artifact>(`/artifacts/${encodeURIComponent(id)}`),
  saveArtifact: (a: Artifact) =>
    jsonFetch<Artifact>("/artifacts", { method: "POST", json: a }),
  refreshArtifact: (id: string) =>
    jsonFetch<Artifact>(`/artifacts/${encodeURIComponent(id)}/refresh`, {
      method: "POST",
    }),
  deleteArtifact: (id: string) =>
    jsonFetch<{ deleted: string }>(`/artifacts/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  uploadArtifact: async (file: File, sessionId: string): Promise<Artifact> => {
    const fd = new FormData()
    fd.append("file", file, file.name)
    fd.append("session_id", sessionId)
    const r = await fetch(`${BACKEND}/artifacts/upload`, {
      method: "POST",
      body: fd,
      headers: authHeaders(),
    })
    if (!r.ok) {
      const detail = await r.text().catch(() => "")
      throw new Error(`upload failed: ${r.status} ${r.statusText} ${detail}`)
    }
    return (await r.json()) as Artifact
  },

  // Tasks
  listTasks: () => jsonFetch<TaskListItem[]>("/tasks"),
  getTask: (id: string) =>
    jsonFetch<SavedTask>(`/tasks/${encodeURIComponent(id)}`),
  updateTask: (id: string, task: SavedTask) =>
    jsonFetch<SavedTask>(`/tasks/${encodeURIComponent(id)}`, {
      method: "PUT",
      json: task,
    }),
  deleteTask: (id: string) =>
    jsonFetch<{ deleted: string }>(`/tasks/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  exportTask: (id: string) =>
    jsonFetch<SavedTask>(`/tasks/${encodeURIComponent(id)}/export`),
  importTask: (task: SavedTask) =>
    jsonFetch<SavedTask>("/tasks/import", { method: "POST", json: task }),
  generateTask: (sessionId: string, model: string) =>
    jsonFetch<SavedTask>("/tasks/generate", {
      method: "POST",
      json: {
        session_id: sessionId,
        model,
      },
    }),
}

export const BACKEND_URL = BACKEND
export const CHAT_URL = `${BACKEND}/chat`
