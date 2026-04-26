"use client"

import { Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export function GeneratingTaskModal({ open }: { open: boolean }) {
  return (
    <Dialog open={open}>
      <DialogContent
        showCloseButton={false}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Generating task…</DialogTitle>
          <DialogDescription>
            The model is reviewing the run, picking the steps that worked, and
            extracting variables. This usually takes a few seconds.
          </DialogDescription>
        </DialogHeader>
        <div
          className="flex items-center gap-3 py-4"
          style={{ color: "var(--ink-2)", fontSize: 14 }}
        >
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Distilling the run into a reusable Task…</span>
        </div>
      </DialogContent>
    </Dialog>
  )
}
