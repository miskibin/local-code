"use client";

import {
  ArrowLeft,
  Check,
  ChevronDown,
  Download,
  Loader2,
  Play,
  Plus,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type CSSProperties,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { getRole, hexAlpha, type TaskRole, TASK_ROLES } from "@/lib/roles";
import { navigateToTaskRunUrl } from "@/lib/tasks";
import type { SavedTask, TaskListItem, TaskRunVariables } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { RunVarsModal } from "../_components/tasks/RunVarsModal";

type SortKey = "recent" | "alpha";

const SORT_LABELS: Record<SortKey, string> = {
  recent: "Recently updated",
  alpha: "A → Z",
};

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [runTask, setRunTask] = useState<SavedTask | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const [q, setQ] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [creator, setCreator] = useState<string>("all");
  const [sort, setSort] = useState<SortKey>("recent");

  const refresh = useCallback(async () => {
    try {
      setTasks(await api.listTasks());
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to list tasks");
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const onDelete = async (id: string) => {
    if (!confirm("Delete this task? This cannot be undone.")) return;
    try {
      await api.deleteTask(id);
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete task");
    }
  };

  const onExport = async (id: string, title: string) => {
    try {
      const exported = await api.exportTask(id);
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/[^a-zA-Z0-9_-]+/g, "_") || "task"}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to export task");
    }
  };

  const onImport = async (file: File) => {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const created = await api.importTask(parsed);
      await refresh();
      toast.success(`Imported "${created.title}"`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to import task");
    }
  };

  const onRunRow = async (id: string) => {
    try {
      const full = await api.getTask(id);
      setRunTask(full);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load task");
    }
  };

  const onRunSubmit = (vars: TaskRunVariables) => {
    if (!runTask) return;
    const taskId = runTask.id;
    setRunTask(null);
    navigateToTaskRunUrl(router, taskId, vars);
  };

  const roleCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const t of tasks) if (t.role) c[t.role] = (c[t.role] || 0) + 1;
    return c;
  }, [tasks]);

  const creatorOptions = useMemo(() => {
    const m = new Map<string, number>();
    for (const t of tasks) if (t.creator) m.set(t.creator, (m.get(t.creator) || 0) + 1);
    return Array.from(m.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [tasks]);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    let out = tasks.filter((t) => {
      if (selectedRoles.length && (!t.role || !selectedRoles.includes(t.role))) return false;
      if (creator !== "all" && t.creator !== creator) return false;
      if (ql) {
        const hay = [
          t.title,
          t.description,
          ...(t.tags || []),
          t.creator || "",
          getRole(t.role)?.label || "",
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(ql)) return false;
      }
      return true;
    });
    if (sort === "alpha") {
      out = [...out].sort((a, b) => a.title.localeCompare(b.title));
    } else {
      out = [...out].sort((a, b) => {
        const av = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const bv = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return bv - av;
      });
    }
    return out;
  }, [tasks, q, selectedRoles, creator, sort]);

  const toggleRole = (id: string) =>
    setSelectedRoles((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  const clearFilters = () => {
    setQ("");
    setSelectedRoles([]);
    setCreator("all");
  };
  const hasFilters = !!q || selectedRoles.length > 0 || creator !== "all";

  return (
    <div className="flex h-dvh flex-col" style={{ background: "var(--bg)" }}>
      <div
        className="flex items-center gap-3 px-6 py-3"
        style={{ borderBottom: "1px solid var(--border)", minHeight: 52 }}
      >
        <Link
          href="/"
          aria-label="Back"
          className="inline-flex items-center justify-center rounded-md p-1.5"
          style={{ color: "var(--ink-2)" }}
        >
          <ArrowLeft className="h-[17px] w-[17px]" />
        </Link>
        <div className="flex flex-1 items-center gap-2">
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              letterSpacing: ".04em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            Tasks
          </span>
          <span style={{ color: "var(--ink-4)", fontSize: 11 }}>·</span>
          <span style={{ fontSize: 13, color: "var(--ink-2)" }}>Marketplace</span>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onImport(f);
            e.target.value = "";
          }}
          style={{ display: "none" }}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => fileInput.current?.click()}
        >
          <Upload className="h-3.5 w-3.5" /> Import JSON
        </Button>
        <Button size="sm">
          <Plus className="h-3.5 w-3.5" /> New task
        </Button>
      </div>

      <div className="flex min-h-0 flex-1">
        <aside
          className="lc-scroll"
          style={{
            width: 244,
            flexShrink: 0,
            borderRight: "1px solid var(--border)",
            background: "var(--bg-sidebar)",
            padding: "18px 14px",
            overflowY: "auto",
          }}
        >
          <FilterHead>Roles</FilterHead>
          {TASK_ROLES.map((r) => (
            <FilterRole
              key={r.id}
              role={r}
              active={selectedRoles.includes(r.id)}
              count={roleCounts[r.id] || 0}
              onClick={() => toggleRole(r.id)}
            />
          ))}

          <div style={{ height: 18 }} />
          <FilterHead>Creator</FilterHead>
          <FilterPill
            active={creator === "all"}
            onClick={() => setCreator("all")}
            count={tasks.length}
          >
            Anyone
          </FilterPill>
          {creatorOptions.map((a) => (
            <FilterPill
              key={a.name}
              active={creator === a.name}
              onClick={() => setCreator(a.name)}
              count={a.count}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
                <Avatar name={a.name} size={16} />
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {a.name}
                </span>
              </span>
            </FilterPill>
          ))}

          {hasFilters && (
            <button
              onClick={clearFilters}
              style={{
                marginTop: 18,
                width: "100%",
                padding: "7px 10px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--bg)",
                color: "var(--ink-2)",
                fontSize: 12,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              <X className="h-3 w-3" /> Clear filters
            </button>
          )}
        </aside>

        <div className="lc-scroll min-w-0 flex-1 overflow-y-auto">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "18px 28px 12px",
              position: "sticky",
              top: 0,
              zIndex: 1,
              background: "linear-gradient(var(--bg) 80%, transparent)",
            }}
          >
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "9px 14px",
                borderRadius: 10,
                background: "var(--bg)",
                border: "1px solid var(--border)",
              }}
            >
              <Search className="h-[15px] w-[15px]" style={{ color: "var(--ink-3)" }} />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search tasks, prompts, tags, or authors…"
                style={{
                  flex: 1,
                  border: 0,
                  outline: 0,
                  background: "transparent",
                  fontSize: 14,
                  color: "var(--ink)",
                }}
              />
              {q && (
                <button
                  onClick={() => setQ("")}
                  title="Clear"
                  style={{
                    background: "transparent",
                    border: 0,
                    color: "var(--ink-3)",
                    cursor: "pointer",
                    padding: 2,
                    display: "inline-flex",
                  }}
                >
                  <X className="h-3 w-3" />
                </button>
              )}
              <kbd
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  padding: "1px 6px",
                  borderRadius: 4,
                  border: "1px solid var(--border)",
                  color: "var(--ink-3)",
                  background: "var(--bg-soft)",
                }}
              >
                ⌘K
              </kbd>
            </div>
            <SortMenu sort={sort} onChange={setSort} />
          </div>

          {(selectedRoles.length > 0 || creator !== "all") && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
                padding: "0 28px 6px",
              }}
            >
              {selectedRoles.map((rid) => {
                const r = getRole(rid);
                return r ? (
                  <ActiveChip
                    key={rid}
                    onRemove={() => toggleRole(rid)}
                    dot={r.color}
                  >
                    {r.label}
                  </ActiveChip>
                ) : null;
              })}
              {creator !== "all" && (
                <ActiveChip onRemove={() => setCreator("all")}>{creator}</ActiveChip>
              )}
            </div>
          )}

          <div style={{ padding: "4px 28px 10px", fontSize: 12, color: "var(--ink-3)" }}>
            {loading
              ? "Loading…"
              : `${filtered.length} ${filtered.length === 1 ? "task" : "tasks"}`}
            {q && !loading ? (
              <>
                {" "}
                matching <span style={{ color: "var(--ink)" }}>“{q}”</span>
              </>
            ) : null}
          </div>

          {loading ? (
            <div
              className="flex items-center gap-2 px-7 py-12"
              style={{ color: "var(--ink-3)" }}
            >
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : tasks.length === 0 ? (
            <div style={{ padding: "0 28px 36px" }}>
              <div
                className="rounded-lg p-10 text-center"
                style={{
                  color: "var(--ink-3)",
                  border: "1px dashed var(--border)",
                }}
              >
                <div style={{ fontSize: 14, marginBottom: 8 }}>No saved tasks yet.</div>
                <div style={{ fontSize: 12 }}>
                  Run something in chat, then click the bookmark icon on the final
                  assistant reply to save it as a task.
                </div>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <EmptyResults onClear={clearFilters} hasFilters={hasFilters} />
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
                gap: 12,
                padding: "0 28px 36px",
              }}
            >
              {filtered.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  role={getRole(t.role)}
                  onOpen={() => router.push(`/tasks/${t.id}`)}
                  onRun={() => void onRunRow(t.id)}
                  onExport={() => void onExport(t.id, t.title)}
                  onDelete={() => void onDelete(t.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <RunVarsModal
        task={runTask}
        open={!!runTask}
        onOpenChange={(open) => {
          if (!open) setRunTask(null);
        }}
        onRun={onRunSubmit}
      />
    </div>
  );
}

function TaskCard({
  task,
  role,
  onOpen,
  onRun,
  onExport,
  onDelete,
}: {
  task: TaskListItem;
  role: TaskRole | undefined;
  onOpen: () => void;
  onRun: () => void;
  onExport: () => void;
  onDelete: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <div
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "var(--bg)",
        border: `1px solid ${hover ? "var(--border-strong)" : "var(--border)"}`,
        borderRadius: 12,
        padding: "14px 16px 12px",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        transition: "border-color .12s, box-shadow .12s",
        boxShadow: hover ? "0 4px 14px -8px rgba(0,0,0,.10)" : "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <RolePill role={role} />
        <span style={{ flex: 1 }} />
      </div>

      <div>
        <div
          style={{
            fontSize: 14.5,
            fontWeight: 600,
            color: "var(--ink)",
            lineHeight: 1.35,
            marginBottom: 4,
          }}
        >
          {task.title || "Untitled"}
        </div>
        <div
          style={{
            fontSize: 12.5,
            color: "var(--ink-2)",
            lineHeight: 1.5,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {task.description || "—"}
        </div>
      </div>

      {task.tags && task.tags.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {task.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: 10.5,
                fontFamily: "var(--font-mono)",
                padding: "2px 7px",
                borderRadius: 999,
                background: "var(--bg-soft)",
                color: "var(--ink-2)",
                border: "1px solid var(--border)",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginTop: "auto",
          paddingTop: 10,
          borderTop: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            minWidth: 0,
            flex: 1,
          }}
        >
          <Avatar name={task.creator || "?"} size={20} />
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
            }}
          >
            <span
              style={{
                fontSize: 12,
                color: "var(--ink)",
                fontWeight: 500,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {task.creator || "—"}
            </span>
            <span style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
              {formatUpdated(task.updated_at)}
            </span>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onExport();
          }}
          title="Export JSON"
          style={iconBtn}
        >
          <Download className="h-3 w-3" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete"
          style={{ ...iconBtn, color: "var(--ink-3)" }}
        >
          <Trash2 className="h-3 w-3" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRun();
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            padding: "5px 10px",
            borderRadius: 6,
            background: hover ? "var(--accent-ink)" : "var(--accent-soft)",
            color: hover ? "#fff" : "var(--accent-ink)",
            border: 0,
            fontSize: 12,
            fontWeight: 500,
            cursor: "pointer",
            transition: "background .12s, color .12s",
          }}
        >
          <Play className="h-3 w-3" /> Run
        </button>
      </div>
    </div>
  );
}

const iconBtn: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 6,
  borderRadius: 6,
  border: 0,
  background: "transparent",
  color: "var(--ink-2)",
  cursor: "pointer",
};

function FilterHead({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: ".04em",
        color: "var(--ink-3)",
        textTransform: "uppercase",
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  count,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count: number;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        padding: "6px 9px",
        borderRadius: 7,
        border: 0,
        background: active ? "var(--hover)" : "transparent",
        color: active ? "var(--ink)" : "var(--ink-2)",
        fontSize: 12.5,
        cursor: "pointer",
        textAlign: "left",
        marginBottom: 1,
        fontWeight: active ? 500 : 400,
      }}
    >
      <span
        style={{
          flex: 1,
          minWidth: 0,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {children}
      </span>
      <span style={{ fontSize: 11, color: "var(--ink-4)" }}>{count}</span>
    </button>
  );
}

function FilterRole({
  role,
  active,
  count,
  onClick,
}: {
  role: TaskRole;
  active: boolean;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        padding: "6px 9px",
        borderRadius: 7,
        border: `1px solid ${active ? role.color : "transparent"}`,
        background: active ? role.soft : "transparent",
        color: active ? role.color : "var(--ink-2)",
        fontSize: 12.5,
        cursor: "pointer",
        textAlign: "left",
        marginBottom: 2,
        fontWeight: active ? 500 : 400,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: role.color,
          flexShrink: 0,
        }}
      />
      <span
        style={{
          flex: 1,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {role.label}
      </span>
      <span style={{ fontSize: 11, color: active ? role.color : "var(--ink-4)" }}>
        {count}
      </span>
    </button>
  );
}

function RolePill({ role }: { role: TaskRole | undefined }) {
  if (!role) {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "2px 8px",
          borderRadius: 999,
          background: "var(--bg-soft)",
          color: "var(--ink-3)",
          fontSize: 10.5,
          fontWeight: 500,
          border: "1px solid var(--border)",
        }}
      >
        unassigned
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "2px 8px",
        borderRadius: 999,
        background: role.soft,
        color: role.color,
        fontSize: 10.5,
        fontWeight: 500,
        letterSpacing: ".02em",
        border: `1px solid ${hexAlpha(role.color, 0.18)}`,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: 999,
          background: role.color,
        }}
      />
      {role.short || role.label}
    </span>
  );
}

function ActiveChip({
  children,
  onRemove,
  dot,
}: {
  children: ReactNode;
  onRemove: () => void;
  dot?: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 4px 3px 9px",
        borderRadius: 999,
        background: "var(--bg-soft)",
        border: "1px solid var(--border)",
        fontSize: 11.5,
        color: "var(--ink-2)",
      }}
    >
      {dot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: dot,
          }}
        />
      )}
      {children}
      <button
        onClick={onRemove}
        style={{
          background: "transparent",
          border: 0,
          padding: 2,
          color: "var(--ink-3)",
          cursor: "pointer",
          display: "inline-flex",
          borderRadius: 999,
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function SortMenu({
  sort,
  onChange,
}: {
  sort: SortKey;
  onChange: (k: SortKey) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "9px 12px",
          borderRadius: 10,
          background: "var(--bg)",
          border: "1px solid var(--border)",
          fontSize: 13,
          color: "var(--ink)",
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}
      >
        <span style={{ color: "var(--ink-3)", fontSize: 12 }}>Sort:</span>
        {SORT_LABELS[sort]}
        <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            right: 0,
            background: "var(--bg)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: 4,
            minWidth: 180,
            boxShadow: "0 12px 36px -12px rgba(0,0,0,.18)",
            zIndex: 4,
          }}
        >
          {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
            <button
              key={k}
              onClick={() => {
                onChange(k);
                setOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                width: "100%",
                padding: "7px 10px",
                borderRadius: 6,
                border: 0,
                background: sort === k ? "var(--hover)" : "transparent",
                color: "var(--ink)",
                cursor: "pointer",
                fontSize: 13,
                textAlign: "left",
              }}
            >
              {sort === k ? (
                <Check className="h-3 w-3" />
              ) : (
                <span style={{ width: 12 }} />
              )}
              {SORT_LABELS[k]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Avatar({ name, size = 22 }: { name: string; size?: number }) {
  const initials = (name || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const hue = hashHue(name || "x");
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: 999,
        display: "inline-grid",
        placeItems: "center",
        background: `oklch(0.86 0.04 ${hue})`,
        color: `oklch(0.32 0.05 ${hue})`,
        fontSize: Math.max(9, size * 0.42),
        fontWeight: 600,
        flexShrink: 0,
        border: `1px solid oklch(0.78 0.04 ${hue})`,
      }}
    >
      {initials || "?"}
    </span>
  );
}

function EmptyResults({
  onClear,
  hasFilters,
}: {
  onClear: () => void;
  hasFilters: boolean;
}) {
  return (
    <div style={{ padding: "48px 28px", textAlign: "center", color: "var(--ink-3)" }}>
      <div
        style={{
          display: "inline-grid",
          placeItems: "center",
          width: 44,
          height: 44,
          borderRadius: 12,
          background: "var(--bg-soft)",
          color: "var(--ink-3)",
          marginBottom: 12,
        }}
      >
        <Search className="h-5 w-5" />
      </div>
      <div
        style={{ fontSize: 14, color: "var(--ink)", fontWeight: 500, marginBottom: 4 }}
      >
        No tasks match
      </div>
      <div style={{ fontSize: 12.5, marginBottom: 14 }}>
        Try a different search or clear filters.
      </div>
      {hasFilters && (
        <button
          onClick={onClear}
          style={{
            padding: "7px 12px",
            borderRadius: 8,
            background: "var(--bg)",
            border: "1px solid var(--border)",
            color: "var(--ink)",
            fontSize: 12.5,
            cursor: "pointer",
          }}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

function formatUpdated(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "—";
  const diff = Date.now() - t;
  const min = 60_000;
  const hour = 60 * min;
  const day = 24 * hour;
  if (diff < min) return "just now";
  if (diff < hour) return `${Math.round(diff / min)}m ago`;
  if (diff < day) return `${Math.round(diff / hour)}h ago`;
  if (diff < 7 * day) return `${Math.round(diff / day)}d ago`;
  return new Date(iso).toLocaleDateString();
}

function hashHue(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % 360;
}
