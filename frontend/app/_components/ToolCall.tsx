"use client"

import { Check, ChevronDown, Loader2, TriangleAlert } from "lucide-react"
import type { ToolStep } from "@/lib/types"
import { DefaultArgs, DefaultResult } from "./tools/default"
import { getToolRenderer } from "./tools"
import { ArtifactChip, useArtifactRefs } from "./ArtifactRefs"

export function ToolCall({
  step,
  toolCallId,
  expanded,
  onToggle,
}: {
  step: ToolStep
  toolCallId?: string
  expanded: boolean
  onToggle: () => void
}) {
  const renderer = getToolRenderer(step.tool)
  const baseStatus = step.status ?? "done"
  const status =
    baseStatus === "done"
      ? (renderer.getStatusOverride?.(step) ?? baseStatus)
      : baseStatus
  const running = status === "running"
  const errored = status === "error"
  const warning = status === "warning"
  const ArgsView = renderer.Args ?? DefaultArgs
  const ResultView = renderer.Result ?? DefaultResult
  const refs = useArtifactRefs()
  const artRef = toolCallId ? refs?.getToolArtifact(toolCallId) : undefined
  const frameBorder = errored
    ? "var(--red)"
    : warning
      ? "var(--amber)"
      : "var(--accent)"

  return (
    <div
      className="lc-reveal my-1 mb-2 overflow-hidden rounded-lg"
      style={{
        border: `1px solid ${frameBorder}`,
        background: "transparent",
      }}
    >
      <button
        onClick={onToggle}
        className="flex w-full cursor-pointer items-center gap-2 px-2.5 py-1.5 text-left"
        style={{
          background: "transparent",
          border: 0,
          borderBottom: expanded ? `1px solid ${frameBorder}` : 0,
          color: "var(--ink)",
        }}
      >
        <span
          className="inline-flex shrink-0"
          style={{
            color: errored
              ? "var(--red)"
              : warning
                ? "var(--amber)"
                : running
                  ? "var(--accent)"
                  : "var(--accent-ink)",
          }}
        >
          {running ? (
            <Loader2 className="lc-spin h-4 w-4" />
          ) : errored || warning ? (
            <TriangleAlert className="h-4 w-4" />
          ) : (
            <Check className="h-4 w-4" />
          )}
        </span>
        {step.taskTitle && (
          <span
            className="rounded-md px-1.5 py-0.5"
            style={{
              fontSize: 11.5,
              color: "var(--ink-2)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              fontWeight: 500,
            }}
          >
            {step.taskTitle}
          </span>
        )}
        {(() => {
          const customLabel = renderer.getHeaderLabel?.(step)
          if (customLabel) {
            return (
              <span className="text-[13.5px]" style={{ color: "var(--ink)" }}>
                {customLabel}
              </span>
            )
          }
          return (
            <>
              <span className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>
                {running ? "Calling" : errored ? "Failed" : "Called"}
              </span>
              <code
                className="font-medium"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 12.5,
                  color: errored
                    ? "var(--red)"
                    : warning
                      ? "var(--amber)"
                      : "var(--accent-ink)",
                }}
              >
                {step.tool}
              </code>
              {warning && (
                <span
                  className="rounded-md px-1.5 py-0.5"
                  style={{
                    fontSize: 11.5,
                    color: "var(--amber)",
                    background: "var(--surface)",
                    border: "1px solid var(--amber)",
                    fontWeight: 500,
                  }}
                >
                  no results
                </span>
              )}
            </>
          )
        })()}
        {step.server && (
          <span
            className="rounded-md px-1.5 py-0.5"
            style={{
              fontSize: 11.5,
              color: "var(--ink-3)",
              fontFamily: "var(--font-mono)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
            }}
          >
            {step.server}
          </span>
        )}
        {artRef && (
          <ArtifactChip
            id={artRef.artifactId}
            title={artRef.title}
            kind={artRef.kind}
          />
        )}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          {step.duration && (
            <span style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
              {step.duration}
            </span>
          )}
          <ChevronDown
            className="h-3.5 w-3.5 transition-transform"
            style={{
              color: "var(--ink-3)",
              transform: expanded ? "rotate(180deg)" : "none",
            }}
          />
        </div>
      </button>
      {expanded && (
        <div style={{ background: "var(--surface)" }}>
          {!renderer.hideArgs && (
            <Section label="Arguments">
              <ArgsView args={step.args} step={step} />
            </Section>
          )}
          <Section label="Result">
            <ResultView result={step.result} status={status} step={step} />
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="px-2.5 pt-2 pb-2 last:pb-2.5">
      <div
        className="mb-1.5 uppercase"
        style={{
          fontSize: 11,
          color: "var(--ink-3)",
          letterSpacing: ".04em",
        }}
      >
        {label}
      </div>
      {children}
    </div>
  )
}
