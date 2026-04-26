"use client"

import { Bot, ChevronDown, Loader2 } from "lucide-react"
import type { Artifact, SubagentStep } from "@/lib/types"
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
  const status = block.status ?? "done"
  const collapseKey = `${msgId}-sa${blockIdx}-collapsed`
  const isCollapsed = !!expanded[collapseKey]
  const toggleCollapsed = () => toggleStep(collapseKey)

  return (
    <>
      <div
        className="lc-reveal mt-2.5 mb-3.5 overflow-hidden rounded-xl"
        style={{
          border: "1px solid var(--accent)",
          borderLeft: "3px solid var(--accent)",
          background: "#fff",
          boxShadow: "0 1px 0 rgba(0,0,0,.02)",
        }}
      >
        <button
          onClick={toggleCollapsed}
          className="flex w-full cursor-pointer items-center gap-3 px-3.5 py-3 text-left"
          style={{
            background: "var(--accent-soft)",
            borderBottom: isCollapsed ? 0 : "1px solid var(--accent)",
            border: 0,
          }}
        >
          <div
            className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg"
            style={{ background: "var(--accent)", color: "#fff" }}
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
                  padding: "2px 7px",
                  background: "#fff",
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
          <div className="px-3.5 pt-2 pb-3">
            {block.steps && block.steps.length > 0 && (
              <div className="relative mt-1 pl-3.5">
                <div
                  className="absolute top-3.5 bottom-3.5 left-1 w-0.5"
                  style={{ background: "var(--accent-soft)" }}
                />
                {block.steps.map((s, i) => (
                  <div key={i} className="relative mb-1.5">
                    <div
                      className="absolute h-2.5 w-2.5 rounded-full"
                      style={{
                        left: -14,
                        top: 18,
                        background:
                          s.status === "running"
                            ? "var(--accent-soft)"
                            : "var(--accent)",
                        border: "2px solid #fff",
                        boxShadow:
                          s.status === "running"
                            ? "0 0 0 2px var(--accent)"
                            : "none",
                      }}
                    />
                    <ToolCall
                      step={s}
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
                className="mt-2 rounded-lg"
                style={{ border: "1px solid var(--accent-soft)" }}
              >
                <summary
                  className="cursor-pointer px-3 py-2 text-[12px] font-medium select-none"
                  style={{ color: "var(--accent-ink)" }}
                >
                  Sub-agent reply
                </summary>
                <div
                  className="px-3 pb-3"
                  style={{ fontSize: 13, color: "var(--ink-2)" }}
                >
                  <Markdown text={block.summary} />
                </div>
              </details>
            )}
          </div>
        )}
      </div>

      {block.artifact && status === "done" && (
        <div className="mb-2.5">
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
            artifact={block.artifact}
            saved={!!savedArtifacts[block.artifact.id]}
            onSave={onSaveArtifact}
            onOpen={onOpenArtifact}
          />
        </div>
      )}
    </>
  )
}
