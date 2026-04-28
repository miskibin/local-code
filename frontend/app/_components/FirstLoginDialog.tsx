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
  getStoredAccent,
  setStoredAccent,
  type AccentName,
} from "@/lib/accent"
import { useAuth } from "@/lib/auth"
import {
  FONT_PRESETS,
  getStoredFontPreset,
  setStoredFontPreset,
  type FontPreset,
} from "@/lib/font-preset"

const ONBOARDING_STORAGE_KEY = "lc-onboarding-v2"

function lookFromStorage(): LookPreset {
  const f = getStoredFontPreset()
  const a = getStoredAccent()
  if (f === "sans" && a === "blue") return "classic"
  if (f === "mono" && a === "teal") return "studio"
  return "classic"
}

const MOCK_CHANGELOG: Record<
  "new" | "old" | "added" | "removed",
  { label: string; items: string[] }
> = {
  new: {
    label: "New",
    items: [
      "Placeholder: first net-new capability in v2.",
      "Placeholder: another headline feature.",
    ],
  },
  old: {
    label: "Old",
    items: [
      "Placeholder: behavior unchanged from v1.",
      "Placeholder: legacy paths still supported.",
    ],
  },
  added: {
    label: "Added",
    items: [
      "Placeholder: UI surface that did not exist before.",
      "Placeholder: optional integration hook.",
    ],
  },
  removed: {
    label: "Removed",
    items: [
      "Placeholder: feature retired — replacement is …",
      "Placeholder: data no longer migrated (mock).",
    ],
  },
}

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
    setLook(lookFromStorage())
    setOpen(true)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [ready, user])

  const persist = useCallback(() => {
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "1")
  }, [])

  const selectLook = useCallback((key: LookPreset) => {
    setLook(key)
    applyLook(key)
  }, [])

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (open && !next) persist()
        setOpen(next)
      }}
    >
      <DialogContent
        className="flex max-h-[min(90vh,880px)] w-[min(96vw,56rem)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-w-none"
        showCloseButton
      >
        <div className="min-h-0 flex-1 overflow-y-auto px-6 pt-6 pb-4">
          <DialogHeader className="gap-2 text-left">
            <DialogTitle className="text-lg">What changed (v1 → v2)</DialogTitle>
            <DialogDescription asChild>
              <p className="text-muted-foreground text-[13px] leading-relaxed">
                Orientation before you continue. Grid below is mocked — replace
                with real release notes when ready.
              </p>
            </DialogDescription>
          </DialogHeader>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(Object.keys(MOCK_CHANGELOG) as (keyof typeof MOCK_CHANGELOG)[]).map(
              (key) => {
                const block = MOCK_CHANGELOG[key]
                return (
                  <section
                    key={key}
                    className="flex min-h-[140px] flex-col rounded-xl border bg-muted/30 p-3"
                    style={{ borderColor: "var(--border)" }}
                  >
                    <h3
                      className="mb-2 shrink-0 border-b pb-2 text-[11px] font-semibold tracking-[0.06em] uppercase"
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--ink-3)",
                        borderColor: "var(--border)",
                      }}
                    >
                      {block.label}
                    </h3>
                    <ul
                      className="text-muted-foreground flex min-h-0 flex-1 list-inside list-disc flex-col gap-1.5 text-[12px] leading-snug"
                      style={{ fontFamily: "var(--lc-body-font)" }}
                    >
                      {block.items.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </section>
                )
              }
            )}
          </div>

          <div className="mt-8 space-y-2 border-t pt-6" style={{ borderColor: "var(--border)" }}>
            <p className="text-foreground text-[13px] font-medium">
              Choose your look
            </p>
            <p className="text-muted-foreground text-[12px] leading-snug">
              Updates apply immediately — same as Appearance in Settings.
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
                    onClick={() => selectLook(key)}
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
        </div>

        <DialogFooter className="border-t bg-muted/30 px-6 py-4 sm:justify-end">
          <Button type="button" className="w-full sm:w-auto" onClick={() => setOpen(false)}>
            Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
