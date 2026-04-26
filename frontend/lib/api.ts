import type { Artifact, MCPServer, Session, StoredMessage, Tool } from "./types";

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL_BASE ?? "http://localhost:8000";

async function jsonFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, ...rest } = init ?? {};
  const r = await fetch(`${BACKEND}${path}`, {
    ...rest,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(rest.headers ?? {}),
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`);
  if (r.status === 204) return undefined as T;
  const ct = r.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) return undefined as T;
  return (await r.json()) as T;
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
  getMessages: (id: string) =>
    jsonFetch<StoredMessage[]>(
      `/sessions/${encodeURIComponent(id)}/messages`,
    ),

  // Tools
  listTools: () => jsonFetch<Tool[]>("/tools"),
  setTool: (name: string, enabled: boolean) =>
    jsonFetch<Tool>(`/tools/${encodeURIComponent(name)}`, {
      method: "PATCH",
      json: { enabled },
    }),

  // MCP
  listMCP: () => jsonFetch<MCPServer[]>("/mcp"),
  upsertMCP: (s: MCPServer) =>
    jsonFetch<MCPServer>("/mcp", { method: "POST", json: s }),
  deleteMCP: (name: string) =>
    jsonFetch<{ deleted: string }>(`/mcp/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

  // Artifacts
  listArtifacts: () => jsonFetch<Artifact[]>("/artifacts"),
  saveArtifact: (a: Artifact) =>
    jsonFetch<Artifact>("/artifacts", { method: "POST", json: a }),
  deleteArtifact: (id: string) =>
    jsonFetch<{ deleted: string }>(`/artifacts/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};

export const BACKEND_URL = BACKEND;
export const CHAT_URL = `${BACKEND}/chat`;
