"use client";

import { Cpu, Database } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type {
  Artifact,
  ArtifactChartPayload,
  ArtifactTablePayload,
} from "@/lib/types";
import { ArtifactTable } from "./ArtifactTable";
import { ArtifactChart } from "./ArtifactChart";

export function ArtifactModal({
  artifact,
  onClose,
}: {
  artifact: Artifact | null;
  onClose: () => void;
}) {
  const open = !!artifact;
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-h-[85vh] max-w-[880px] overflow-hidden p-0">
        <DialogHeader className="px-5 py-3.5" style={{ borderBottom: "1px solid var(--border)" }}>
          <DialogTitle className="flex items-center gap-2.5 text-sm font-medium">
            <span className="inline-flex" style={{ color: "var(--accent)" }}>
              {artifact?.kind === "table" ? (
                <Database className="h-4 w-4" />
              ) : (
                <Cpu className="h-4 w-4" />
              )}
            </span>
            {artifact?.title}
          </DialogTitle>
        </DialogHeader>
        <div className="overflow-auto" style={{ maxHeight: "calc(85vh - 60px)" }}>
          {artifact?.kind === "table" ? (
            <ArtifactTable payload={artifact.payload as ArtifactTablePayload} />
          ) : artifact ? (
            <ArtifactChart payload={artifact.payload as ArtifactChartPayload} />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
