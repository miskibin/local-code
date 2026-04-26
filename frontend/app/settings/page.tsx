"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Cpu,
  Database,
  Folder,
  Globe,
  Plus,
  Server,
  Terminal,
  Trash2,
  Wrench,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { MCPServer, Tool } from "@/lib/types";
import { AddServerDialog } from "../_components/AddServerDialog";

const MODEL_NAME = process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "gemma4:e4b";

export default function SettingsPage() {
  const [tab, setTab] = useState("mcp");
  return (
    <div className="flex h-dvh flex-col" style={{ background: "var(--bg)" }}>
      <div
        className="flex items-center gap-3 px-6 py-3.5"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <Link
          href="/"
          aria-label="Back"
          className="inline-flex items-center justify-center rounded-md p-1.5"
          style={{ color: "var(--ink-2)" }}
        >
          <ArrowLeft className="h-[17px] w-[17px]" />
        </Link>
        <div className="text-[15px] font-semibold" style={{ color: "var(--ink)" }}>
          Settings
        </div>
      </div>

      <Tabs
        value={tab}
        onValueChange={setTab}
        className="flex min-h-0 flex-1"
        orientation="vertical"
      >
        <div
          className="flex w-[200px] flex-shrink-0 flex-col gap-1 px-3 py-4"
          style={{
            background: "var(--bg-soft)",
            borderRight: "1px solid var(--border)",
          }}
        >
          <TabsList className="flex h-auto w-full flex-col items-stretch gap-0.5 bg-transparent p-0">
            <TabsTrigger value="mcp" className="justify-start gap-2.5 px-2.5 py-2">
              <Server className="h-3.5 w-3.5" /> MCP servers
            </TabsTrigger>
            <TabsTrigger value="tools" className="justify-start gap-2.5 px-2.5 py-2">
              <Wrench className="h-3.5 w-3.5" /> Tools
            </TabsTrigger>
            <TabsTrigger value="model" className="justify-start gap-2.5 px-2.5 py-2">
              <Cpu className="h-3.5 w-3.5" /> Model
            </TabsTrigger>
          </TabsList>
        </div>
        <div className="lc-scroll flex-1 overflow-y-auto px-10 py-8">
          <div className="mx-auto max-w-[760px]">
            <TabsContent value="mcp">
              <McpTab />
            </TabsContent>
            <TabsContent value="tools">
              <ToolsTab />
            </TabsContent>
            <TabsContent value="model">
              <ModelTab />
            </TabsContent>
          </div>
        </div>
      </Tabs>
    </div>
  );
}

function SectionHeader({
  title,
  desc,
  right,
}: {
  title: string;
  desc?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-[20px] font-semibold" style={{ letterSpacing: "-.01em" }}>
          {title}
        </h2>
        {desc && (
          <p className="mt-1 text-[13px]" style={{ color: "var(--ink-2)" }}>
            {desc}
          </p>
        )}
      </div>
      {right}
    </div>
  );
}

function McpTab() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [open, setOpen] = useState(false);

  const reload = useCallback(async () => {
    try {
      setServers(await api.listMCP());
    } catch (e) {
      console.error("listMCP", e);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const onToggle = async (s: MCPServer, enabled: boolean) => {
    await api.upsertMCP({ ...s, enabled });
    await reload();
  };

  const onDelete = async (name: string) => {
    await api.deleteMCP(name);
    await reload();
  };

  const onAdd = async (s: MCPServer) => {
    await api.upsertMCP(s);
    await reload();
  };

  return (
    <>
      <SectionHeader
        title="MCP servers"
        desc="Model Context Protocol servers expose tools the agent can call. Servers run locally."
        right={
          <Button onClick={() => setOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" /> Add server
          </Button>
        }
      />
      <div
        className="overflow-hidden rounded-xl"
        style={{ border: "1px solid var(--border)", background: "#fff" }}
      >
        {servers.length === 0 && (
          <div className="px-4 py-6 text-center text-[13px]" style={{ color: "var(--ink-3)" }}>
            No MCP servers configured. Click <strong>Add server</strong> to add one.
          </div>
        )}
        {servers.map((s, i) => (
          <McpRow
            key={s.name}
            server={s}
            first={i === 0}
            onToggle={(v) => onToggle(s, v)}
            onDelete={() => onDelete(s.name)}
          />
        ))}
      </div>
      <p className="mt-3.5 text-xs" style={{ color: "var(--ink-3)" }}>
        Servers are launched as subprocesses on app start. Configuration lives in the
        backend SQLite database.
      </p>
      <AddServerDialog open={open} onOpenChange={setOpen} onAdd={onAdd} />
    </>
  );
}

function McpRow({
  server,
  first,
  onToggle,
  onDelete,
}: {
  server: MCPServer;
  first: boolean;
  onToggle: (v: boolean) => void;
  onDelete: () => void;
}) {
  const conn = server.connection ?? {};
  const cmd = [conn.command ?? "", ...((conn.args as string[] | undefined) ?? [])]
    .join(" ")
    .trim();
  const Icon = guessIcon(server.name);
  return (
    <div
      className="flex items-center gap-3.5 px-4 py-3.5"
      style={{ borderTop: first ? 0 : "1px solid var(--border)" }}
    >
      <div
        className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg"
        style={{
          background: "var(--bg-soft)",
          border: "1px solid var(--border)",
          color: "var(--ink-2)",
        }}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13.5, color: "var(--ink)" }}>
            {server.name}
          </span>
          <StatusBadge enabled={server.enabled} />
        </div>
        {cmd && (
          <div
            className="mt-1 truncate"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11.5,
              color: "var(--ink-3)",
            }}
          >
            {cmd}
          </div>
        )}
      </div>
      <Switch checked={server.enabled} onCheckedChange={onToggle} aria-label={`Toggle ${server.name}`} />
      <button
        onClick={onDelete}
        title="Delete"
        className="rounded-md p-1.5 transition"
        style={{ background: "transparent", color: "var(--ink-3)", border: 0 }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--hover)";
          e.currentTarget.style.color = "var(--red)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = "var(--ink-3)";
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11.5px] font-medium"
      style={{
        background: enabled ? "var(--green-soft)" : "#f4f4f4",
        color: enabled ? "var(--green)" : "var(--ink-3)",
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: enabled ? "var(--green)" : "var(--ink-4)" }}
      />
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}

function guessIcon(name: string) {
  const n = name.toLowerCase();
  if (n.includes("file") || n.includes("fs")) return Folder;
  if (n.includes("web") || n.includes("http") || n.includes("fetch")) return Globe;
  if (n.includes("sql") || n.includes("db")) return Database;
  if (n.includes("shell") || n.includes("term")) return Terminal;
  return Server;
}

function ToolsTab() {
  const [tools, setTools] = useState<Tool[]>([]);

  const reload = useCallback(async () => {
    try {
      setTools(await api.listTools());
    } catch (e) {
      console.error("listTools", e);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const enabledCount = useMemo(() => tools.filter((t) => t.enabled).length, [tools]);

  const grouped = useMemo(() => {
    const m: Record<string, Tool[]> = {};
    for (const t of tools) {
      const server = t.name.includes("_")
        ? t.name.slice(0, t.name.indexOf("_"))
        : "local";
      (m[server] ||= []).push(t);
    }
    return m;
  }, [tools]);

  const onToggle = async (name: string, enabled: boolean) => {
    setTools((p) => p.map((t) => (t.name === name ? { ...t, enabled } : t)));
    try {
      await api.setTool(name, enabled);
    } catch (e) {
      console.error("setTool", e);
      reload();
    }
  };

  return (
    <>
      <SectionHeader
        title="Tools"
        desc={`${enabledCount} of ${tools.length} tools available to the agent. Disabled tools are hidden from the model entirely.`}
      />
      <div
        className="overflow-hidden rounded-xl"
        style={{ border: "1px solid var(--border)", background: "#fff" }}
      >
        {Object.entries(grouped).map(([server, list], gi) => (
          <div
            key={server}
            style={{ borderTop: gi === 0 ? 0 : "1px solid var(--border)" }}
          >
            <div
              className="px-4 py-2 uppercase"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                fontWeight: 500,
                letterSpacing: ".04em",
                color: "var(--ink-3)",
                background: "var(--bg-soft)",
                borderBottom: "1px solid var(--border)",
              }}
            >
              {server}
            </div>
            {list.map((t, i) => (
              <div
                key={t.name}
                className="flex items-center gap-3.5 px-4 py-3"
                style={{ borderTop: i === 0 ? 0 : "1px solid var(--border)" }}
              >
                <div className="min-w-0 flex-1">
                  <div
                    style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink)" }}
                  >
                    {t.name}
                  </div>
                  {t.description && (
                    <div className="mt-0.5 text-[12.5px]" style={{ color: "var(--ink-2)" }}>
                      {t.description}
                    </div>
                  )}
                </div>
                <Switch
                  checked={t.enabled}
                  onCheckedChange={(v) => onToggle(t.name, v)}
                  aria-label={`Toggle ${t.name}`}
                />
              </div>
            ))}
          </div>
        ))}
        {tools.length === 0 && (
          <div
            className="px-4 py-6 text-center text-[13px]"
            style={{ color: "var(--ink-3)" }}
          >
            No tools discovered.
          </div>
        )}
      </div>
    </>
  );
}

function ModelTab() {
  const fields = [
    { k: "Model", v: MODEL_NAME, mono: true },
    { k: "Provider", v: "Local (Ollama)" },
    { k: "Parameters", v: "9.6B (E4B)" },
    { k: "Context window", v: "128k tokens" },
    { k: "Quantization", v: "Q4_K_M", mono: true },
    { k: "Endpoint", v: "http://localhost:11434", mono: true },
  ];
  return (
    <>
      <SectionHeader
        title="Model"
        desc="The local model the agent uses. All inference runs on-device via Ollama."
      />
      <div
        className="mb-6 overflow-hidden rounded-xl"
        style={{ border: "1px solid var(--border)", background: "#fff" }}
      >
        <div
          className="flex items-center gap-3.5 px-4 py-3.5"
          style={{ background: "var(--accent-soft)" }}
        >
          <div
            className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-lg"
            style={{
              background: "#fff",
              border: "1px solid var(--accent)",
              color: "var(--accent-ink)",
            }}
          >
            <Cpu className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className="text-[14px] font-medium"
                style={{ fontFamily: "var(--font-mono)", color: "var(--ink)" }}
              >
                {MODEL_NAME}
              </span>
              <span
                className="rounded uppercase"
                style={{
                  fontSize: 10,
                  padding: "1px 6px",
                  background: "#fff",
                  color: "var(--accent-ink)",
                  fontWeight: 500,
                  letterSpacing: ".02em",
                  border: "1px solid var(--accent)",
                }}
              >
                Recommended
              </span>
            </div>
            <div className="mt-1 text-xs" style={{ color: "var(--ink-2)" }}>
              Native tools · 128k context · 9.6 GB
            </div>
          </div>
          <CheckCircle2 className="h-5 w-5" style={{ color: "var(--accent)" }} />
        </div>
      </div>

      <h3
        className="mb-2.5 uppercase"
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "var(--ink-2)",
          letterSpacing: ".04em",
        }}
      >
        Active model details
      </h3>
      <div
        className="overflow-hidden rounded-xl"
        style={{ border: "1px solid var(--border)", background: "#fff" }}
      >
        {fields.map((f, i) => (
          <div
            key={f.k}
            className="flex items-center justify-between px-5 py-2.5 text-[13px]"
            style={{ borderTop: i === 0 ? 0 : "1px solid var(--border)" }}
          >
            <span style={{ color: "var(--ink-2)" }}>{f.k}</span>
            <span
              style={{
                fontFamily: f.mono ? "var(--font-mono)" : "inherit",
                color: "var(--ink)",
              }}
            >
              {f.v}
            </span>
          </div>
        ))}
      </div>

      <div
        className="mt-6 flex items-start gap-2 rounded-lg p-3"
        style={{
          background: "var(--amber-soft)",
          border: "1px solid #fde68a",
          color: "var(--amber)",
        }}
      >
        <AlertCircle className="h-4 w-4 flex-shrink-0" />
        <div className="text-xs">
          Model selection is read from <code style={{ fontFamily: "var(--font-mono)" }}>OLLAMA_MODEL</code>.
          Switching models requires updating the backend config and restart.
        </div>
      </div>
    </>
  );
}
