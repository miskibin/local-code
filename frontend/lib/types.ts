export type Session = {
  id: string
  title: string
  is_pinned?: boolean
}

export type SessionPatch = {
  title?: string
  is_pinned?: boolean
}

export type FilePart = {
  type: "file"
  artifactId: string
  mediaType: string
  name?: string
}

export type StoredMessage = {
  id: string
  role: "user" | "assistant"
  parts: ({ type: "text"; text: string } | FilePart)[]
}

export type Tool = {
  name: string
  enabled: boolean
  description: string
}

export type MCPServer = {
  name: string
  enabled: boolean
  connection: {
    transport?: "stdio" | "sse" | "http"
    command?: string
    args?: string[]
    env?: Record<string, string>
    url?: string
  }
}

export type ArtifactColumn = {
  key: string
  label: string
  numeric?: boolean
  format?: "currency"
}

export type ArtifactTablePayload = {
  columns: ArtifactColumn[]
  rows: Record<string, string | number | null>[]
}

export type ArtifactImagePayload = {
  format: "png"
  data_b64: string
  caption?: string | null
}

export type ArtifactTextPayload = {
  text?: string
  text_preview?: string
  stderr?: string | null
}

export type ArtifactUploadPayload = {
  path?: string
  mime?: string
  size?: number
  filename?: string
  summary_md?: string
  n_rows?: number
  n_cols?: number
  columns?: { name: string; dtype: string }[]
  text_preview?: string
}

export type ArtifactSourceKind = "python" | "sql" | "text" | "upload"

export type Artifact = {
  id: string
  session_id?: string | null
  kind: "table" | "image" | "text"
  title: string
  payload:
    | ArtifactTablePayload
    | ArtifactImagePayload
    | ArtifactTextPayload
    | ArtifactUploadPayload
  summary?: string
  source_kind?: ArtifactSourceKind | null
  source_code?: string | null
  parent_artifact_ids?: string[]
  payload_size?: number
  pinned?: boolean
  created_at?: string
  updated_at?: string
}

export type ToolStep = {
  kind: "tool"
  tool: string
  server: string
  args: Record<string, unknown>
  result: string
  duration?: string
  status?: "running" | "done" | "error"
  toolCallId?: string
  taskTitle?: string
}

export type SubagentStep = {
  kind: "subagent"
  agent: { id: string; name: string }
  task: string
  duration?: string
  status?: "running" | "done" | "error"
  statusText?: string
  steps?: ToolStep[]
  artifact?: Artifact
  summary?: string
}

export type AssistantStep = ToolStep | SubagentStep

export type TodoStatus = "pending" | "in_progress" | "completed"
export type Todo = { content: string; status: TodoStatus }

export type TaskVariableType = "string" | "number" | "boolean"

export type TaskVariable = {
  name: string
  type: TaskVariableType
  label: string
  default: unknown
  required: boolean
}

export type TaskStepKind = "tool" | "code" | "subagent" | "prompt"
export type TaskStepOutputKind = "rows" | "text" | "chart" | "json" | "file"

export type TaskStep = {
  id: string
  kind: TaskStepKind
  title: string
  server?: string | null
  tool?: string | null
  args_template?: Record<string, unknown> | null
  code?: string | null
  subagent?: string | null
  prompt?: string | null
  output_name: string
  output_kind: TaskStepOutputKind
}

export type SavedTask = {
  id: string
  title: string
  description: string
  source_session_id?: string | null
  variables: TaskVariable[]
  steps: TaskStep[]
  created_at?: string | null
  updated_at?: string | null
}

export type TaskListItem = {
  id: string
  title: string
  description: string
  updated_at?: string | null
}

export type TaskRunVariables = Record<string, string | number | boolean>
