"use client"

import { Bot, ChevronDown, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import type { Artifact, SubagentStep } from "@/lib/types"
import { useArtifactRefs } from "./ArtifactRefs"
import { Markdown } from "./Markdown"
import { ToolCall } from "./ToolCall"
import { ArtifactCard } from "./Artifact"

export function Subagent({
  block,
  expanded,
  toggleStep,
  savedArtifacts,
  onSaveArtifact,
  onOpenArtifact,
  msgId,
  blockIdx,
}: {
  block: SubagentStep
  expanded: Record<string, boolean>
  toggleStep: (key: string) => void
  savedArtifacts: Record<string, boolean>
  onSaveArtifact: (a: Artifact) => void
  onOpenArtifact: (a: Artifact) => void
  msgId: string
  blockIdx: number
}) {
  const tableRefreshCtx = useArtifactRefs()
  const [tableRefreshed, setTableRefreshed] = useState<Artifact | null>(null)
  const onTableRefreshFromCtx = tableRefreshCtx?.onTableRefresh
  const status = block.status ?? "done"
  const saArtifact = block.artifact
  useEffect(() => {
    setTableRefreshed(null)
  }, [saArtifact?.id])
  const collapseKey = `${msgId}-sa${blockIdx}-collapsed`
  const isCollapsed = !!expanded[collapseKey]
  const toggleCollapsed = () => toggleStep(collapseKey)

  return (
    <>
      <div
        className="lc-reveal mt-1.5 mb-2 overflow-hidden rounded-lg"
        style={{
          border: "1px solid var(--accent)",
          borderLeft: "3px solid var(--accent)",
          background: "transparent",
        }}
      >
        <button
          onClick={toggleCollapsed}
          className="flex w-full cursor-pointer items-center gap-2.5 px-2.5 py-2 text-left"
          style={{
            background: "transparent",
            borderBottom: isCollapsed ? 0 : "1px solid var(--accent)",
            border: 0,
          }}
        >
          <div
            className="grid h-7 w-7 flex-shrink-0 place-items-center rounded-md"
            style={{
              background: "var(--accent)",
              color: "var(--accent-foreground)",
            }}
          >
            <Bot className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className="text-[13.5px] font-semibold"
                style={{ color: "var(--ink)" }}
              >
                {block.agent.name}
              </span>
              <span
                className="rounded uppercase"
                style={{
                  fontSize: 10.5,
                  padding: "1px 6px",
                  background: "transparent",
                  color: "var(--accent-ink)",
                  border: "1px solid var(--accent)",
                  fontWeight: 500,
                  letterSpacing: ".04em",
                }}
              >
                Subagent
              </span>
              {status === "running" && (
                <span
                  className="inline-flex"
                  style={{ color: "var(--accent-ink)" }}
                >
                  <Loader2 className="lc-spin h-3.5 w-3.5" />
                </span>
              )}
              {status === "done" && block.steps && (
                <span style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                  · {block.steps.length} step
                  {block.steps.length === 1 ? "" : "s"}
                </span>
              )}
            </div>
            <div
              className="mt-0.5"
              style={{ fontSize: 12, color: "var(--ink-2)" }}
            >
              {block.task}
            </div>
          </div>
          {block.duration && status === "done" && (
            <span
              className="mr-1.5"
              style={{
                fontSize: 11.5,
                color: "var(--accent-ink)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {block.duration}
            </span>
          )}
          <ChevronDown
            className="h-4 w-4 transition-transform"
            style={{
              color: "var(--accent-ink)",
              transform: isCollapsed ? "none" : "rotate(180deg)",
            }}
          />
        </button>

        {!isCollapsed && (
          <div className="px-2.5 pt-1.5 pb-2">
            {block.steps && block.steps.length > 0 && (
              <div className="relative mt-0.5 pl-3">
                <div
                  className="absolute top-3 bottom-3 left-1 w-px"
                  style={{ background: "var(--accent)" }}
                />
                {block.steps.map((s, i) => (
                  <div key={i} className="relative mb-1.5">
                    <div
                      className="absolute h-2.5 w-2.5 rounded-full"
                      style={{
                        left: -13,
                        top: 15,
                        background:
                          s.status === "running"
                            ? "var(--accent-soft)"
                            : "var(--accent)",
                        border: "2px solid var(--bg)",
                        boxShadow:
                          s.status === "running"
                            ? "0 0 0 2px var(--accent)"
                            : "none",
                      }}
                    />
                    <ToolCall
                      step={s}
                      toolCallId={s.toolCallId}
                      expanded={!!expanded[`${msgId}-sa${blockIdx}-${i}`]}
                      onToggle={() => toggleStep(`${msgId}-sa${blockIdx}-${i}`)}
                    />
                  </div>
                ))}
              </div>
            )}

            {status === "running" && block.statusText && (
              <div
                className="inline-flex items-center gap-2 px-1 py-2"
                style={{ fontSize: 13, color: "var(--ink-2)" }}
              >
                <Loader2 className="lc-spin h-3.5 w-3.5" />
                <span>{block.statusText}</span>
                <span>
                  <span className="lc-dot" />
                  <span className="lc-dot" />
                  <span className="lc-dot" />
                </span>
              </div>
            )}

            {block.summary && status === "done" && (
              <details
                className="mt-1.5 rounded-md"
                style={{ border: "1px solid var(--border)" }}
              >
                <summary
                  className="cursor-pointer px-2 py-1.5 text-[12px] font-medium select-none"
                  style={{ color: "var(--accent-ink)" }}
                >
                  Sub-agent reply
                </summary>
                <div
                  className="px-2 pb-2"
                  style={{ fontSize: 13, color: "var(--ink-2)" }}
                >
                  <Markdown text={block.summary} />
                </div>
              </details>
            )}
          </div>
        )}
      </div>

      {saArtifact && status === "done" && (
        <div className="mb-2">
          <div
            className="mb-1.5 flex items-center gap-1.5 pl-0.5 uppercase"
            style={{
              fontSize: 11,
              color: "var(--ink-3)",
              letterSpacing: ".04em",
            }}
          >
            <span className="inline-flex" style={{ color: "var(--accent)" }}>
              <Bot className="h-3 w-3" />
            </span>
            Returned by {block.agent.name}
          </div>
          <ArtifactCard
            artifact={tableRefreshed ?? saArtifact}
            saved={!!savedArtifacts[saArtifact.id]}
            onSave={onSaveArtifact}
            onOpen={
              saArtifact.kind === "table" ? undefined : onOpenArtifact
            }
            onTableRefresh={
              saArtifact.kind === "table" && onTableRefreshFromCtx
                ? async (a) => {
                    const f = await onTableRefreshFromCtx(a)
                    setTableRefreshed(f)
                    return f
                  }
                : undefined
            }
          />
        </div>
      )}
    </>
  )
}
