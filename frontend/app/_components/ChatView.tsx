"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { api, CHAT_URL } from "@/lib/api";

const DEFAULT_MODEL =
  process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "gemma4:e4b";
import type {
  Artifact,
  AssistantStep,
  SubagentStep,
  Todo,
  ToolStep,
} from "@/lib/types";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import {
  AssistantMessage,
  contentBlocksToPlainText,
  UserMessage,
} from "./Messages";
import type { AssistantMsg, ContentBlock } from "./Messages";

export type AnyPart = {
  type: string;
  text?: string;
  toolCallId?: string;
  toolName?: string;
  state?: string;
  input?: unknown;
  output?: unknown;
  errorText?: string;
  data?: unknown;
  id?: string;
  callProviderMetadata?: Record<string, Record<string, unknown>>;
  resultProviderMetadata?: Record<string, Record<string, unknown>>;
};

export type ArtifactDataPart = {
  toolCallId: string;
  artifactId: string;
  kind: "table" | "image" | "text";
  title: string;
  summary: string;
  updatedAt: string;
};

export function extractArtifactIds(parts: AnyPart[]): string[] {
  const out: string[] = [];
  for (const p of parts) {
    if (p.type !== "data-artifact") continue;
    const data = p.data as ArtifactDataPart | undefined;
    if (data?.artifactId) out.push(data.artifactId);
  }
  return out;
}

function getParentToolCallId(p: AnyPart): string | null {
  const sub =
    (p.resultProviderMetadata?.subagent as
      | Record<string, unknown>
      | undefined) ??
    (p.callProviderMetadata?.subagent as Record<string, unknown> | undefined);
  const parent = sub?.parentToolCallId;
  return typeof parent === "string" ? parent : null;
}

function isToolPart(p: AnyPart): boolean {
  return p.type === "dynamic-tool" || p.type.startsWith("tool-");
}

function getToolName(p: AnyPart): string | null {
  if (p.type === "dynamic-tool") return p.toolName ?? null;
  if (p.type.startsWith("tool-")) return p.type.slice(5);
  return null;
}

function extractTodos(p: AnyPart): Todo[] | null {
  if (getToolName(p) !== "write_todos") return null;
  const input = p.input as { todos?: unknown } | undefined;
  if (!input || !Array.isArray(input.todos) || input.todos.length === 0) {
    return null;
  }
  const todos: Todo[] = [];
  for (const t of input.todos) {
    if (typeof t !== "object" || t === null) continue;
    const obj = t as { content?: unknown; status?: unknown };
    const content = typeof obj.content === "string" ? obj.content : "";
    const status: Todo["status"] =
      obj.status === "completed" || obj.status === "in_progress"
        ? obj.status
        : "pending";
    todos.push({ content, status });
  }
  return todos.length > 0 ? todos : null;
}

function prettifyAgentName(id: string): string {
  return id
    .split(/[-_]/)
    .filter(Boolean)
    .map((s) => s[0].toUpperCase() + s.slice(1))
    .join(" ");
}

function partToToolStep(p: AnyPart): ToolStep | null {
  let toolName: string | null = null;
  if (p.type === "dynamic-tool") toolName = p.toolName ?? null;
  else if (p.type.startsWith("tool-")) toolName = p.type.slice(5);
  if (!toolName) return null;
  const state = p.state ?? "input-available";
  const status: ToolStep["status"] =
    state === "output-available"
      ? "done"
      : state === "output-error"
        ? "error"
        : "running";
  let result = "";
  if (state === "output-available")
    result =
      typeof p.output === "string" ? p.output : JSON.stringify(p.output ?? "");
  else if (state === "output-error") result = p.errorText ?? "error";
  else result = "…";
  const server = toolName.includes("_") ? toolName.split("_")[0] : "local";
  const args =
    typeof p.input === "object" && p.input !== null
      ? (p.input as Record<string, unknown>)
      : { _input: p.input };
  return {
    kind: "tool",
    tool: toolName,
    server,
    args,
    result,
    status,
  };
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
function partsToContentBlocks(parts: AnyPart[]): ContentBlock[] {
  // Pass 1 — collect every tool part keyed by its toolCallId, plus its parent
  // link if any.
  const stepByCallId = new Map<string, ToolStep>();
  const partByCallId = new Map<string, AnyPart>();
  const parentOf = new Map<string, string>();
  const childrenOf = new Map<string, string[]>();

  for (const p of parts) {
    if (!isToolPart(p) || !p.toolCallId) continue;
    const step = partToToolStep(p);
    if (!step) continue;
    stepByCallId.set(p.toolCallId, step);
    partByCallId.set(p.toolCallId, p);
    const parent = getParentToolCallId(p);
    if (parent) {
      parentOf.set(p.toolCallId, parent);
      const arr = childrenOf.get(parent) ?? [];
      arr.push(p.toolCallId);
      childrenOf.set(parent, arr);
    }
  }

  if (process.env.NEXT_PUBLIC_DEBUG === "1") {
    for (const [child, parent] of parentOf) {
      if (!stepByCallId.has(parent)) {
        console.debug("[chat] orphan tool parent", { child, parent });
      }
    }
  }

  // Pass 1.5 — collect `write_todos` state. The agent calls it repeatedly to
  // mutate statuses; each call replaces the entire list. We render a single
  // plan block at the position of the first call, using the latest non-empty
  // todos. Streaming = latest call's output hasn't arrived.
  let firstWriteTodosCallId: string | null = null;
  let latestTodos: Todo[] | null = null;
  let latestWriteTodosState: string | undefined;
  const writeTodosCallIds = new Set<string>();
  for (const p of parts) {
    if (getToolName(p) !== "write_todos" || !p.toolCallId) continue;
    writeTodosCallIds.add(p.toolCallId);
    if (firstWriteTodosCallId === null) firstWriteTodosCallId = p.toolCallId;
    const todos = extractTodos(p);
    if (todos) {
      latestTodos = todos;
      latestWriteTodosState = p.state;
    }
  }
  const planStreaming = latestWriteTodosState
    ? latestWriteTodosState !== "output-available" &&
      latestWriteTodosState !== "output-error"
    : false;

  // Pass 2 — walk parts in stream order. Skip tool parts that have a known
  // parent (they're rendered as nested children below). Group children whose
  // parent has any sub-tools into a SubagentStep.
  const out: ContentBlock[] = [];
  let textAcc = "";
  const flush = () => {
    if (textAcc.length > 0) {
      out.push({ type: "text", text: textAcc });
      textAcc = "";
    }
  };

  for (const p of parts) {
    if (p.type === "text") {
      textAcc += p.text ?? "";
      continue;
    }
    if (!isToolPart(p) || !p.toolCallId) continue;

    // Collapse all write_todos calls into one plan block at the first call.
    if (writeTodosCallIds.has(p.toolCallId)) {
      if (p.toolCallId === firstWriteTodosCallId && latestTodos) {
        flush();
        out.push({
          type: "plan",
          todos: latestTodos,
          streaming: planStreaming,
        });
      }
      continue;
    }

    // Has a parent that we know about → consumed by parent's SubagentStep.
    const parentId = parentOf.get(p.toolCallId);
    if (parentId && stepByCallId.has(parentId)) continue;

    flush();
    const childIds = childrenOf.get(p.toolCallId) ?? [];
    const ownStep = stepByCallId.get(p.toolCallId)!;
    if (childIds.length === 0) {
      out.push({ type: "step", step: ownStep });
    } else {
      out.push({ type: "step", step: buildSubagentStep(ownStep, childIds, stepByCallId) });
    }
  }
  flush();
  return out;
}

function buildSubagentStep(
  parent: ToolStep,
  childIds: string[],
  stepByCallId: Map<string, ToolStep>,
): SubagentStep {
  const args = parent.args ?? {};
  const subagentType =
    typeof args.subagent_type === "string" ? args.subagent_type : "subagent";
  const description =
    typeof args.description === "string" ? args.description : parent.tool;
  const children: ToolStep[] = [];
  for (const cid of childIds) {
    const s = stepByCallId.get(cid);
    if (s) children.push(s);
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
  };
}

function partsToText(parts: AnyPart[]): string {
  return parts
    .filter((p) => p.type === "text")
    .map((p) => p.text ?? "")
    .join("");
}

function mergeSeedSteps(
  blocks: ContentBlock[],
  isLast: boolean,
  seedSteps: AssistantStep[] | undefined,
): ContentBlock[] {
  const fromParts = blocks.some((b) => b.type === "step");
  if (fromParts || !isLast || !seedSteps?.length) return blocks;
  return [
    ...seedSteps.map((s) => ({ type: "step" as const, step: s })),
    ...blocks,
  ];
}

export const __testing__ = { partsToContentBlocks, extractArtifactIds };

type Props = {
  sessionId: string;
  onFirstUserMessage: (text: string) => void;
  savedArtifacts: Record<string, boolean>;
  onSaveArtifact: (a: Artifact) => Promise<void> | void;
  onOpenArtifact: (a: Artifact) => void;
  seedSteps?: AssistantStep[];
  seedArtifacts?: Artifact[];
  demoUserText?: string;
  demoAssistantText?: string;
};

export function ChatView({
  sessionId,
  onFirstUserMessage,
  savedArtifacts,
  onSaveArtifact,
  onOpenArtifact,
  seedSteps,
  seedArtifacts,
  demoUserText,
  demoAssistantText,
}: Props) {
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: CHAT_URL,
        prepareSendMessagesRequest: ({ id, messages, body, trigger }) => {
          const b = body as
            | { reset?: boolean; model?: string }
            | undefined;
          return {
            body: {
              id,
              messages: messages.map((m) => ({
                id: m.id,
                role: m.role,
                parts: (m.parts ?? [])
                  .filter((p) => p.type === "text")
                  .map((p) => ({
                    type: "text",
                    text: (p as { text: string }).text,
                  })),
              })),
              reset:
                trigger === "regenerate-message" || b?.reset === true,
              model: b?.model ?? selectedModel,
            },
          };
        },
      }),
    [selectedModel],
  );
  const { messages, sendMessage, regenerate, setMessages, status, stop } =
    useChat({
      id: sessionId,
      transport,
      onError: (e) => toast.error(e.message ?? "Stream error"),
    });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [demoSeen, setDemoSeen] = useState(false);
  const [artifactCache, setArtifactCache] = useState<Record<string, Artifact>>(
    {},
  );
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentFirstRef = useRef(false);

  const streaming = status === "streaming" || status === "submitted";

  useEffect(() => {
    setExpanded({});
    sentFirstRef.current = false;
    if (sessionId === "demo-subagent") {
      setMessages([]);
      return;
    }
    let cancelled = false;
    api
      .getMessages(sessionId)
      .then((m) => {
        if (cancelled) return;
        setMessages(m);
        if (m.length > 0) sentFirstRef.current = true;
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, setMessages]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const allIds = new Set<string>();
    for (const m of messages) {
      for (const id of extractArtifactIds((m.parts ?? []) as AnyPart[])) {
        allIds.add(id);
      }
    }
    const missing = Array.from(allIds).filter((id) => !artifactCache[id]);
    if (missing.length === 0) return;
    let cancelled = false;
    Promise.all(
      missing.map((id) =>
        api.getArtifact(id).then(
          (a) => [id, a] as const,
          () => null,
        ),
      ),
    ).then((results) => {
      if (cancelled) return;
      setArtifactCache((prev) => {
        const next = { ...prev };
        for (const r of results) {
          if (r) next[r[0]] = r[1];
        }
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [messages, artifactCache]);

  useEffect(() => {
    if (sentFirstRef.current) return;
    const firstUser = messages.find((m) => m.role === "user");
    if (!firstUser) return;
    const text = firstUser.parts
      .filter((p) => p.type === "text")
      .map((p) => (p as { text: string }).text)
      .join("");
    if (text) {
      sentFirstRef.current = true;
      onFirstUserMessage(text);
    }
  }, [messages, onFirstUserMessage]);

  const toggleStep = (key: string) =>
    setExpanded((p) => ({ ...p, [key]: !p[key] }));

  const showDemo = !!demoUserText && messages.length === 0;
  const isEmpty = messages.length === 0 && !demoSeen && !showDemo;

  const send = (text: string) => {
    setDemoSeen(true);
    sendMessage({ text });
  };

  const handleRegenerate = (assistantId: string) =>
    void regenerate({ messageId: assistantId });

  const handleEdit = (userId: string, newText: string) => {
    const idx = messages.findIndex((m) => m.id === userId);
    if (idx < 0) return;
    setMessages((prev) => prev.slice(0, idx));
    sendMessage({ text: newText }, { body: { reset: true } });
  };

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i].id;
    }
    return null;
  }, [messages]);

  return (
    <div
      className="flex min-w-0 flex-1 flex-col"
      style={{ background: "var(--bg)" }}
    >
      <div ref={scrollRef} className="lc-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-5xl px-6 pb-12 pt-8">
          {isEmpty ? (
            <EmptyState onPick={send} />
          ) : showDemo ? (
            <div>
              <UserMessage text={demoUserText!} />
              <AssistantMessage
                msg={{
                  id: "demo-assistant",
                  contentBlocks: [
                    ...(seedSteps ?? []).map((s) => ({
                      type: "step" as const,
                      step: s,
                    })),
                    { type: "text" as const, text: demoAssistantText ?? "" },
                  ],
                  artifacts: seedArtifacts,
                }}
                expanded={expanded}
                toggleStep={toggleStep}
                isLast={true}
                streaming={false}
                savedArtifacts={savedArtifacts}
                onSaveArtifact={(a) => void onSaveArtifact(a)}
                onOpenArtifact={onOpenArtifact}
              />
            </div>
          ) : (
            <div>
              {messages.map((m) => {
                const parts = (m.parts ?? []) as AnyPart[];
                const text = partsToText(parts);
                if (m.role === "user") {
                  return (
                    <UserMessage
                      key={m.id}
                      text={text}
                      onEdit={
                        streaming
                          ? undefined
                          : (newText) => handleEdit(m.id, newText)
                      }
                    />
                  );
                }
                const isLast = m.id === lastAssistantId;
                const contentBlocks = mergeSeedSteps(
                  partsToContentBlocks(parts),
                  isLast,
                  seedSteps,
                );
                const liveArtifacts = extractArtifactIds(parts)
                  .map((id) => artifactCache[id])
                  .filter((a): a is Artifact => !!a);
                const msg: AssistantMsg = {
                  id: m.id,
                  contentBlocks,
                  artifacts:
                    liveArtifacts.length > 0
                      ? liveArtifacts
                      : isLast
                        ? seedArtifacts
                        : undefined,
                };
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
                        contentBlocksToPlainText(msg.contentBlocks),
                      )
                    }
                    onRegenerate={
                      streaming ? undefined : () => handleRegenerate(m.id)
                    }
                  />
                );
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
        <Composer
          onSend={send}
          onStop={() => stop()}
          streaming={streaming}
          model={selectedModel}
          onModelChange={setSelectedModel}
        />
      </div>
    </div>
  );
}
