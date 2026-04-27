"use client"

import Link from "next/link"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type ErrorStateProps = {
  kind: "404" | "500"
  onPrimary?: () => void
  primaryHref?: string
  secondaryHref?: string
}

export default function ErrorState({
  kind,
  onPrimary,
  primaryHref = "/",
  secondaryHref = "/",
}: ErrorStateProps) {
  const is500 = kind === "500"
  const code = is500 ? "500" : "404"
  const subtitle = is500 ? "runtime fault" : "route not found"
  const traceId = is500 ? "b1-7c8" : "4f-9b2"
  const heading = is500
    ? "The model crashed mid-thought."
    : "We couldn't find that."
  const body = is500
    ? "The local runtime tripped on the last token. Your conversation is safe — try sending the message again."
    : "The chat you're looking for doesn't exist, or was already cleared from this device."

  const primaryLabel = is500 ? "Try again" : "Back to chat"
  const secondaryLabel = is500 ? "Back to chat" : "New chat"

  return (
    <div className="lc-error flex min-h-screen flex-col bg-background">
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-8 py-12 text-center">
        <div
          className="mono-strip lc-reveal mb-7"
          style={{ animationDelay: "0s" }}
        >
          <span className={is500 ? "pulse-dot red" : "pulse-dot"} />
          <span style={is500 ? { color: "var(--red)" } : undefined}>
            {code} · {subtitle} · {traceId}
          </span>
        </div>

        <div
          className={cn("numeral lc-reveal", is500 && "red")}
          style={{ animationDelay: ".05s" }}
        >
          {code}
        </div>

        <h1
          className="lc-reveal mt-7 mb-2 text-[22px] font-medium tracking-[-0.015em]"
          style={{ animationDelay: ".18s" }}
        >
          {heading}
        </h1>
        <p
          className="lc-reveal mb-7 max-w-[420px] text-sm"
          style={{ animationDelay: ".24s", color: "var(--ink-2)" }}
        >
          {body}
        </p>

        <div
          className="lc-reveal inline-flex gap-2"
          style={{ animationDelay: ".32s" }}
        >
          {is500 ? (
            <Button onClick={onPrimary}>{primaryLabel}</Button>
          ) : (
            <Button asChild>
              <Link href={primaryHref}>{primaryLabel}</Link>
            </Button>
          )}
          <Button variant="outline" asChild>
            <Link href={is500 ? primaryHref : secondaryHref}>
              {secondaryLabel}
            </Link>
          </Button>
        </div>

        <div
          className="lc-reveal mt-8 text-[11px] font-[var(--font-mono)]"
          style={{ animationDelay: ".4s", color: "var(--ink-4)" }}
        >
          or press <kbd className="key">⌘</kbd> <kbd className="key">K</kbd> to
          search chats
        </div>
      </div>
    </div>
  )
}
