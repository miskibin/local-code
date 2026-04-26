"use client";

import { formatDistanceToNow } from "date-fns";
import { Cpu, Database, FileText, RotateCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type {
  Artifact,
  ArtifactChartPayload,
  ArtifactTablePayload,
  ArtifactTextPayload,
} from "@/lib/types";

import { ArtifactChart } from "./ArtifactChart";
import { ArtifactSourceCode } from "./ArtifactSourceCode";
import { ArtifactTable } from "./ArtifactTable";

function KindIcon({ kind }: { kind: Artifact["kind"] }) {
  if (kind === "table") return <Database className="h-4 w-4" />;
  if (kind === "chart") return <Cpu className="h-4 w-4" />;
  return <FileText className="h-4 w-4" />;
}

function UpdatedPill({ ts }: { ts?: string }) {
  if (!ts) return null;
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return null;
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[11px]"
      style={{ background: "var(--bg-soft)", color: "var(--ink-3)" }}
    >
      Updated {formatDistanceToNow(d, { addSuffix: true })}
    </span>
  );
}

export function ArtifactModal({
  artifact,
  onClose,
  onRefreshed,
}: {
  artifact: Artifact | null;
  onClose: () => void;
  onRefreshed?: (a: Artifact) => void;
}) {
  const [refreshing, setRefreshing] = useState(false);
  const open = !!artifact;

  const handleRefresh = async () => {
    if (!artifact) return;
    setRefreshing(true);
    try {
      const fresh = await api.refreshArtifact(artifact.id);
      onRefreshed?.(fresh);
      toast.success("Artifact refreshed");
    } catch (e) {
      toast.error(`Refresh failed: ${(e as Error).message}`);
    } finally {
      setRefreshing(false);
    }
  };

  const canRefresh = !!artifact?.source_code && !!artifact?.source_kind;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="w-[95vw] max-w-[1400px] sm:max-w-[1400px] max-h-[90vh] overflow-hidden p-0">
        <DialogHeader
          className="flex flex-row items-center gap-3 px-5 py-3.5"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <span className="inline-flex" style={{ color: "var(--accent)" }}>
            {artifact ? <KindIcon kind={artifact.kind} /> : null}
          </span>
          <DialogTitle className="flex-1 text-sm font-medium">
            {artifact?.title}
          </DialogTitle>
          <UpdatedPill ts={artifact?.updated_at} />
          {canRefresh ? (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition disabled:opacity-50"
              style={{
                background: "var(--accent)",
                color: "#fff",
                border: 0,
                cursor: refreshing ? "default" : "pointer",
              }}
              data-testid="artifact-refresh"
              title="Re-run the source script and update the payload"
            >
              <RotateCw
                className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
              />
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
          ) : null}
        </DialogHeader>
        <div
          className="overflow-auto px-5 pb-5 pt-3"
          style={{ maxHeight: "calc(90vh - 60px)" }}
        >
          {artifact?.kind === "table" ? (
            <ArtifactTable payload={artifact.payload as ArtifactTablePayload} />
          ) : artifact?.kind === "chart" ? (
            <ArtifactChart payload={artifact.payload as ArtifactChartPayload} />
          ) : artifact?.kind === "text" ? (
            <pre
              className="whitespace-pre-wrap rounded-lg p-3"
              style={{
                background: "var(--bg-soft)",
                fontFamily: "var(--font-mono)",
                fontSize: 12.5,
                color: "var(--ink-2)",
              }}
            >
              {(artifact.payload as ArtifactTextPayload).text}
            </pre>
          ) : null}
          {artifact ? (
            <ArtifactSourceCode
              sourceKind={artifact.source_kind ?? null}
              sourceCode={artifact.source_code ?? null}
            />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
