"use client"

import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import type { MCPServer } from "@/lib/types"

type Form = {
  name: string
  command: string
  args: string
  env: string
  transport: "stdio" | "sse" | "http"
}

const EMPTY: Form = {
  name: "",
  command: "npx",
  args: "",
  env: "",
  transport: "stdio",
}

export function AddServerDialog({
  open,
  onOpenChange,
  onAdd,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onAdd: (server: MCPServer) => Promise<void> | void
}) {
  const [form, setForm] = useState<Form>(EMPTY)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) setForm(EMPTY)
  }, [open])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    const env: Record<string, string> = {}
    for (const line of form.env.split(/\r?\n/)) {
      const t = line.trim()
      if (!t) continue
      const eq = t.indexOf("=")
      if (eq > 0) env[t.slice(0, eq).trim()] = t.slice(eq + 1).trim()
    }
    setSubmitting(true)
    try {
      await onAdd({
        name: form.name.trim(),
        enabled: true,
        connection: {
          transport: form.transport,
          command: form.command.trim() || undefined,
          args: form.args
            .split(/\s+/)
            .map((s) => s.trim())
            .filter(Boolean),
          env: Object.keys(env).length ? env : undefined,
        },
      })
      onOpenChange(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[520px] overflow-hidden p-0">
        <form onSubmit={submit}>
          <DialogHeader
            className="px-5 py-4"
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <DialogTitle>Add MCP server</DialogTitle>
            <DialogDescription>
              The server will be launched as a subprocess.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3.5 px-5 py-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="srv-name">Name</Label>
              <Input
                id="srv-name"
                placeholder="my-server"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                autoFocus
              />
              <span className="text-xs" style={{ color: "var(--ink-3)" }}>
                A short identifier — e.g. filesystem
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Transport</Label>
              <div
                className="flex gap-1.5 rounded-lg p-1"
                style={{
                  background: "var(--bg-soft)",
                  border: "1px solid var(--border)",
                }}
              >
                {(["stdio", "sse", "http"] as const).map((t) => (
                  <button
                    type="button"
                    key={t}
                    onClick={() => setForm((f) => ({ ...f, transport: t }))}
                    className={cn("flex-1 rounded-md px-2.5 py-1.5 text-xs")}
                    style={{
                      fontFamily: "var(--font-mono)",
                      background:
                        form.transport === t ? "var(--surface)" : "transparent",
                      color:
                        form.transport === t ? "var(--ink)" : "var(--ink-2)",
                      border: 0,
                      cursor: "pointer",
                      boxShadow:
                        form.transport === t
                          ? "0 1px 2px rgba(0,0,0,.06)"
                          : "none",
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="srv-cmd">Command</Label>
              <Input
                id="srv-cmd"
                value={form.command}
                onChange={(e) =>
                  setForm((f) => ({ ...f, command: e.target.value }))
                }
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="srv-args">Arguments</Label>
              <Input
                id="srv-args"
                placeholder="-y @modelcontextprotocol/server-x"
                value={form.args}
                onChange={(e) =>
                  setForm((f) => ({ ...f, args: e.target.value }))
                }
                style={{ fontFamily: "var(--font-mono)" }}
              />
              <span className="text-xs" style={{ color: "var(--ink-3)" }}>
                Space-separated
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="srv-env">Environment variables</Label>
              <Textarea
                id="srv-env"
                rows={3}
                placeholder={"API_KEY=sk-...\nPATH=/usr/local/bin"}
                value={form.env}
                onChange={(e) =>
                  setForm((f) => ({ ...f, env: e.target.value }))
                }
                style={{
                  fontFamily: "var(--font-mono)",
                  minHeight: 70,
                  resize: "vertical",
                }}
              />
              <span className="text-xs" style={{ color: "var(--ink-3)" }}>
                One per line, KEY=value
              </span>
            </div>
          </div>
          <DialogFooter
            className="flex justify-end gap-2 px-5 py-3.5"
            style={{
              background: "var(--bg-soft)",
              borderTop: "1px solid var(--border)",
            }}
          >
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !form.name.trim()}>
              Add server
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
