"use client"

import type { LanguageModelUsage } from "ai"
import {
  Context,
  ContextContent,
  ContextContentHeader,
  ContextTrigger,
} from "@/components/ai-elements/context"
import type { UsageDataPart } from "./ChatView"

const HARD_CAP_TOKENS = 256_000
const LOCAL_CAP_TOKENS = 16_384

function defaultMaxFor(modelId?: string): number {
  if (!modelId) return LOCAL_CAP_TOKENS
  if (modelId.startsWith("gemini")) return HARD_CAP_TOKENS
  return LOCAL_CAP_TOKENS
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
  const out = usage?.outputTokens ?? 0
  return (
    <Context
      usedTokens={used}
      maxTokens={cappedMax}
      modelId={modelId}
      usage={
        {
          inputTokens: used,
          outputTokens: out,
          totalTokens: used + out,
        } as LanguageModelUsage
      }
    >
      <ContextTrigger className="h-6 w-6 p-0 [&_svg]:h-3.5 [&_svg]:w-3.5 [&>span]:hidden" />
      <ContextContent align="center" className="min-w-56">
        <ContextContentHeader />
        {overCap ? (
          <div className="px-3 pb-3 text-[11px] text-muted-foreground">
            Capped at 256k. Past this point models lose accuracy on long-context
            recall.
          </div>
        ) : null}
      </ContextContent>
    </Context>
  )
}
