export type Session = {
  id: string;
  title: string;
};

export type StoredMessage = {
  id: string;
  role: "user" | "assistant";
  parts: { type: "text"; text: string }[];
};

export type Tool = {
  name: string;
  enabled: boolean;
  description: string;
};

export type MCPServer = {
  name: string;
  enabled: boolean;
  connection: {
    transport?: "stdio" | "sse" | "http";
    command?: string;
    args?: string[];
    env?: Record<string, string>;
    url?: string;
  };
};

export type ArtifactColumn = {
  key: string;
  label: string;
  numeric?: boolean;
  format?: "currency";
};

export type ArtifactTablePayload = {
  columns: ArtifactColumn[];
  rows: Record<string, string | number | null>[];
};

export type ArtifactChartPoint = { label: string; value: number };

export type ArtifactChartPayload = {
  data: ArtifactChartPoint[];
  caption?: string;
};

export type ArtifactTextPayload = {
  text: string;
  stderr?: string | null;
};

export type ArtifactSourceKind = "python" | "sql" | "chart" | "text";

export type Artifact = {
  id: string;
  session_id?: string | null;
  kind: "table" | "chart" | "text";
  title: string;
  payload: ArtifactTablePayload | ArtifactChartPayload | ArtifactTextPayload;
  summary?: string;
  source_kind?: ArtifactSourceKind | null;
  source_code?: string | null;
  parent_artifact_ids?: string[];
  payload_size?: number;
  created_at?: string;
  updated_at?: string;
};

export type ToolStep = {
  kind: "tool";
  tool: string;
  server: string;
  args: Record<string, unknown>;
  result: string;
  duration?: string;
  status?: "running" | "done" | "error";
};

export type SubagentStep = {
  kind: "subagent";
  agent: { id: string; name: string };
  task: string;
  duration?: string;
  status?: "running" | "done" | "error";
  statusText?: string;
  steps?: ToolStep[];
  artifact?: Artifact;
  summary?: string;
};

export type AssistantStep = ToolStep | SubagentStep;

export type TodoStatus = "pending" | "in_progress" | "completed";
export type Todo = { content: string; status: TodoStatus };
