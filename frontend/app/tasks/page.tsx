"use client";

import {
  ArrowLeft,
  Download,
  Loader2,
  Play,
  Plus,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { navigateToTaskRunUrl } from "@/lib/tasks";
import type { SavedTask, TaskListItem, TaskRunVariables } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { RunVarsModal } from "../_components/tasks/RunVarsModal";

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [runTask, setRunTask] = useState<SavedTask | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    try {
      setTasks(await api.listTasks());
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Failed to list tasks",
      );
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
      toast.error(
        e instanceof Error ? e.message : "Failed to export task",
      );
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

  return (
    <div className="flex h-dvh flex-col" style={{ background: "var(--bg)" }}>
      <div
        className="flex items-center gap-3 px-6 py-3"
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
          Tasks
        </div>
        <div className="flex-1" />
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
      </div>

      <div className="lc-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl px-6 py-8">
          {loading ? (
            <div
              className="flex items-center gap-2 py-12"
              style={{ color: "var(--ink-3)" }}
            >
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : tasks.length === 0 ? (
            <div
              className="rounded-lg p-10 text-center"
              style={{
                color: "var(--ink-3)",
                border: "1px dashed var(--border)",
              }}
            >
              <div style={{ fontSize: 14, marginBottom: 8 }}>
                No saved tasks yet.
              </div>
              <div style={{ fontSize: 12 }}>
                Run something in chat, then click the bookmark icon on the
                final assistant reply to save it as a task.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {tasks.map((t) => (
                <div
                  key={t.id}
                  className="flex flex-col gap-2 rounded-lg p-4"
                  style={{
                    background: "var(--bg-soft)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <Link
                    href={`/tasks/${t.id}`}
                    className="block"
                    style={{ color: "var(--ink)" }}
                  >
                    <div
                      className="truncate font-medium"
                      style={{ fontSize: 15 }}
                    >
                      {t.title || "Untitled"}
                    </div>
                    <div
                      className="mt-1 line-clamp-2"
                      style={{ fontSize: 12, color: "var(--ink-3)" }}
                    >
                      {t.description || "—"}
                    </div>
                  </Link>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Button
                      size="sm"
                      onClick={() => void onRunRow(t.id)}
                      className="h-7 text-[12px]"
                    >
                      <Play className="h-3 w-3" /> Run
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void onExport(t.id, t.title)}
                      className="h-7 text-[12px]"
                      title="Export JSON"
                    >
                      <Download className="h-3 w-3" />
                    </Button>
                    <div className="flex-1" />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void onDelete(t.id)}
                      className="h-7 text-[12px]"
                      title="Delete"
                      style={{ color: "var(--ink-3)" }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
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
