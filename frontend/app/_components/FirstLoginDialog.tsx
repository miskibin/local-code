"use client"

import { Check } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  ACCENTS,
  setStoredAccent,
  type AccentName,
} from "@/lib/accent"
import { useAuth } from "@/lib/auth"
import {
  FONT_PRESETS,
  setStoredFontPreset,
  type FontPreset,
} from "@/lib/font-preset"

const ONBOARDING_STORAGE_KEY = "lc-onboarding-v2"

const MOCK_RELEASE_NOTES = [
  "Placeholder: overview of what shipped in v2.",
  "Placeholder: redesigned areas (you will list these later).",
  "Placeholder: data migration notes — what carries over, what does not.",
]

type LookPreset = "classic" | "studio"

const LOOKS: Record<
  LookPreset,
  { title: string; subtitle: string; font: FontPreset; accent: AccentName }
> = {
  classic: {
    title: "Classic",
    subtitle: "Sans body text and blue accents — familiar and calm.",
    font: "sans",
    accent: "blue",
  },
  studio: {
    title: "Studio",
    subtitle: "Monospace body and teal accents — tighter, terminal-inspired.",
    font: "mono",
    accent: "teal",
  },
}

function applyLook(preset: LookPreset) {
  const { font, accent } = LOOKS[preset]
  setStoredFontPreset(font)
  setStoredAccent(accent)
}

export function FirstLoginDialog() {
  const { user, ready } = useAuth()
  const [open, setOpen] = useState(false)
  const [look, setLook] = useState<LookPreset>("classic")

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- open once after auth + localStorage read on client */
    if (!ready || !user) return
    if (typeof window === "undefined") return
    if (window.localStorage.getItem(ONBOARDING_STORAGE_KEY)) return
    setOpen(true)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [ready, user])

  const persist = useCallback(() => {
    applyLook(look)
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "1")
  }, [look])

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (open && !next) persist()
        setOpen(next)
      }}
    >
      <DialogContent className="gap-4 sm:max-w-lg" showCloseButton>
        <DialogHeader className="gap-2 text-left">
          <DialogTitle>What changed (v1 → v2)</DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-3">
              <p className="text-muted-foreground text-[13px] leading-relaxed">
                Quick orientation before you jump in. Details below are mocked —
                replace with real release notes when ready.
              </p>
              <ul className="text-muted-foreground list-inside list-disc space-y-1.5 text-[13px] leading-relaxed">
                {MOCK_RELEASE_NOTES.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <p className="text-foreground text-[13px] font-medium">
            Choose your look
          </p>
          <p className="text-muted-foreground text-[12px] leading-snug">
            Same choices as Appearance in Settings — pick one to start.
          </p>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {(Object.keys(LOOKS) as LookPreset[]).map((key) => {
              const cfg = LOOKS[key]
              const active = look === key
              const accentColor = ACCENTS[cfg.accent].color
              const stack = FONT_PRESETS[cfg.font].stack
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setLook(key)}
                  aria-pressed={active}
                  className="rounded-lg border p-3 text-left outline-none transition-[border-color,background-color,box-shadow] duration-150 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--popover)]"
                  style={{
                    cursor: "pointer",
                    borderColor: active ? accentColor : "var(--border)",
                    background: active
                      ? `color-mix(in oklab, ${accentColor} 12%, var(--popover))`
                      : "var(--muted)",
                    boxShadow: active
                      ? `0 0 0 1px ${accentColor}, 0 4px 14px -4px color-mix(in oklab, ${accentColor} 35%, transparent)`
                      : undefined,
                  }}
                >
                  <div
                    className="mb-2 h-1 w-full rounded-sm"
                    style={{ background: accentColor }}
                  />
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold">{cfg.title}</span>
                        {active && (
                          <Check
                            className="h-3.5 w-3.5 shrink-0"
                            style={{ color: accentColor }}
                            strokeWidth={2.5}
                            aria-hidden
                          />
                        )}
                      </div>
                      <p
                        className="text-muted-foreground mt-1 text-[11.5px] leading-snug"
                        style={{ fontFamily: stack }}
                      >
                        {cfg.subtitle}
                      </p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <DialogFooter className="gap-2 border-t-0 p-0 pt-1 sm:justify-end">
          <Button type="button" className="w-full sm:w-auto" onClick={() => setOpen(false)}>
            Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
