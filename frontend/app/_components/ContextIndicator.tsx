"use client"

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import type { UsageDataPart } from "./ChatView"

const HARD_CAP_TOKENS = 256_000
const LOCAL_CAP_TOKENS = 16_384
const AUTO_SUMMARY_FRACTION = 0.85

function defaultMaxFor(modelId?: string): number {
  if (!modelId) return LOCAL_CAP_TOKENS
  if (modelId.startsWith("gemini")) return HARD_CAP_TOKENS
  return LOCAL_CAP_TOKENS
}

const compact = new Intl.NumberFormat("en-US", { notation: "compact" })
const pct = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
})

const ICON_RADIUS = 10
const ICON_VIEWBOX = 24
const ICON_CENTER = 12
const ICON_STROKE = 2

function Ring({ ratio }: { ratio: number }) {
  const r = Math.max(0, Math.min(1, ratio))
  const circ = 2 * Math.PI * ICON_RADIUS
  const offset = circ * (1 - r)
  return (
    <svg
      aria-label="Model context usage"
      role="img"
      viewBox={`0 0 ${ICON_VIEWBOX} ${ICON_VIEWBOX}`}
      className="h-4 w-4"
      style={{ color: "currentcolor" }}
    >
      <circle
        cx={ICON_CENTER}
        cy={ICON_CENTER}
        r={ICON_RADIUS}
        fill="none"
        opacity="0.25"
        stroke="currentColor"
        strokeWidth={ICON_STROKE}
      />
      <circle
        cx={ICON_CENTER}
        cy={ICON_CENTER}
        r={ICON_RADIUS}
        fill="none"
        opacity="0.85"
        stroke="currentColor"
        strokeDasharray={`${circ} ${circ}`}
        strokeDashoffset={offset}
        strokeLinecap="round"
        strokeWidth={ICON_STROKE}
        style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
      />
    </svg>
  )
}

export function ContextIndicator({
  usage,
  model,
}: {
  usage?: UsageDataPart
  model?: string
}) {
  const modelId = usage?.modelId ?? model
  const rawMax = usage?.contextMaxTokens ?? defaultMaxFor(modelId)
  if (rawMax <= 0) return null
  const cappedMax = Math.min(rawMax, HARD_CAP_TOKENS)
  const overCap = rawMax > HARD_CAP_TOKENS
  const used = usage?.inputTokens ?? 0
  const ratio = used / cappedMax
  const overflow = ratio > 1
  const visualRatio = Math.min(1, ratio)
  const summaryThreshold = Math.round(cappedMax * AUTO_SUMMARY_FRACTION)
  return (
    <HoverCard openDelay={0} closeDelay={0}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          aria-label="Context usage"
          className="inline-flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-muted"
          style={{
            color: overflow
              ? "var(--red, #dc2626)"
              : ratio >= AUTO_SUMMARY_FRACTION
                ? "var(--amber, #d97706)"
                : "var(--ink-2, currentcolor)",
          }}
        >
          <Ring ratio={visualRatio} />
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="center" className="min-w-60 p-3">
        <div className="flex items-center justify-between gap-3 text-xs">
          <span>{pct.format(ratio)}</span>
          <span className="font-mono text-muted-foreground">
            {compact.format(used)} / {compact.format(cappedMax)}
          </span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-[width]"
            style={{
              width: `${visualRatio * 100}%`,
              background: overflow
                ? "var(--red, #dc2626)"
                : ratio >= AUTO_SUMMARY_FRACTION
                  ? "var(--amber, #d97706)"
                  : "var(--accent, currentcolor)",
            }}
          />
        </div>
        <p className="mt-2 text-[11px] text-muted-foreground">
          Auto-summary fires near {compact.format(summaryThreshold)} tokens
          (~85%).
        </p>
        {overflow ? (
          <p className="mt-1 text-[11px]" style={{ color: "var(--red)" }}>
            Over budget. Compaction should trigger on the next turn.
          </p>
        ) : null}
        {overCap ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Capped at 256k. Past this point models lose accuracy on long-context
            recall.
          </p>
        ) : null}
      </HoverCardContent>
    </HoverCard>
  )
}
