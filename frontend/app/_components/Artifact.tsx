"use client";

import { Check, Cpu, Database, MoreHorizontal, Plus } from "lucide-react";
import type {
  Artifact as ArtifactT,
  ArtifactChartPayload,
  ArtifactTablePayload,
} from "@/lib/types";
import { ArtifactTable } from "./ArtifactTable";
import { ArtifactChart } from "./ArtifactChart";

export function ArtifactCard({
  artifact,
  saved,
  onSave,
  onOpen,
}: {
  artifact: ArtifactT;
  saved: boolean;
  onSave: (a: ArtifactT) => void;
  onOpen: (a: ArtifactT) => void;
}) {
  const isTable = artifact.kind === "table";
  const tablePayload = isTable ? (artifact.payload as ArtifactTablePayload) : null;
  const chartPayload = !isTable ? (artifact.payload as ArtifactChartPayload) : null;
  const meta = isTable
    ? `${tablePayload!.rows?.length ?? 0} rows · ${tablePayload!.columns?.length ?? 0} columns`
    : `${artifact.kind} · svg`;
  return (
    <div
      className="lc-reveal mb-3.5 mt-2 overflow-hidden rounded-xl"
      style={{ border: "1px solid var(--border)", background: "#fff" }}
    >
      <div
        className="flex items-center gap-2.5 px-3.5 py-2.5"
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-soft)",
        }}
      >
        <span className="inline-flex" style={{ color: "var(--accent)" }}>
          {isTable ? <Database className="h-3.5 w-3.5" /> : <Cpu className="h-3.5 w-3.5" />}
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="text-[13px] font-medium" style={{ color: "var(--ink)" }}>
            {artifact.title}
          </div>
          <div
            className="mt-0.5"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11.5,
              color: "var(--ink-3)",
            }}
          >
            {meta}
          </div>
        </div>
        <button
          onClick={() => onOpen(artifact)}
          title="Open"
          className="rounded-md p-1.5 transition"
          style={{ background: "transparent", color: "var(--ink-2)" }}
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => onSave(artifact)}
          disabled={saved}
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 transition"
          style={{
            background: saved ? "transparent" : "var(--accent)",
            color: saved ? "var(--ink-2)" : "#fff",
            fontSize: 12,
            fontWeight: 500,
            border: saved ? "1px solid var(--border)" : 0,
            cursor: saved ? "default" : "pointer",
          }}
        >
          {saved ? (
            <>
              <Check className="h-3 w-3" /> Saved
            </>
          ) : (
            <>
              <Plus className="h-3 w-3" /> Save
            </>
          )}
        </button>
      </div>
      {isTable ? (
        <ArtifactTable payload={tablePayload!} />
      ) : (
        <ArtifactChart payload={chartPayload!} />
      )}
    </div>
  );
}
