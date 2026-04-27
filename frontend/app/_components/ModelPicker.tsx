"use client"

import { Check, ChevronDown, Cpu } from "lucide-react"
import { useEffect, useRef, useState } from "react"

const DEFAULT_MODEL = process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? "gemma4:e4b"

const MODELS = [
  {
    id: "gemma4-e4b",
    name: DEFAULT_MODEL,
    desc: "Native tools · 128k ctx",
    size: "9.6 GB",
    recommended: true,
  },
  {
    id: "nemotron-3-super:cloud",
    name: "nemotron-3-super:cloud",
    desc: "Cloud · fast",
    size: "—",
  },
  {
    id: "gemini-3.1-flash-lite-preview",
    name: "gemini-3.1-flash-lite-preview",
    desc: "Google · cloud",
    size: "—",
  },
  {
    id: "gemini-3-flash-preview",
    name: "gemini-3-flash-preview",
    desc: "Google · cloud",
    size: "—",
  },
]

type ModelPickerProps = {
  value?: string
  onChange?: (modelName: string) => void
}

export function ModelPicker({ value, onChange }: ModelPickerProps = {}) {
  const [open, setOpen] = useState(false)
  const [internal, setInternal] = useState(MODELS[0].name)
  const selectedName = value ?? internal
  const ref = useRef<HTMLDivElement | null>(null)
  const current = MODELS.find((m) => m.name === selectedName) ?? MODELS[0]

  const pick = (name: string) => {
    setInternal(name)
    onChange?.(name)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title="Change model"
        className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-2)",
          fontFamily: "var(--font-mono)",
          fontSize: 12,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--hover)"
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent"
        }}
      >
        <Cpu className="h-3.5 w-3.5" />
        <span>{current.name}</span>
        <ChevronDown
          className="h-3 w-3 transition-transform"
          style={{ transform: open ? "rotate(180deg)" : "none" }}
        />
      </button>
      {open && (
        <div
          className="lc-reveal absolute left-0 z-30 min-w-[280px] rounded-xl p-1"
          style={{
            bottom: "calc(100% + 8px)",
            background: "var(--popover)",
            border: "1px solid var(--border)",
            boxShadow:
              "0 12px 32px -8px rgba(0,0,0,.18), 0 2px 6px rgba(0,0,0,.04)",
          }}
        >
          <div
            className="px-3 pt-2 pb-1 uppercase"
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "var(--ink-3)",
              letterSpacing: ".04em",
            }}
          >
            Local models
          </div>
          {MODELS.map((m) => (
            <button
              key={m.id}
              onClick={() => pick(m.name)}
              className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left"
              style={{ background: "transparent", border: 0 }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--hover)"
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent"
              }}
            >
              <div
                className="grid h-6 w-6 flex-shrink-0 place-items-center rounded-md"
                style={{
                  background: "var(--bg-soft)",
                  border: "1px solid var(--border)",
                  color: "var(--ink-2)",
                }}
              >
                <Cpu className="h-3 w-3" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 13,
                      color: "var(--ink)",
                    }}
                  >
                    {m.name}
                  </span>
                  {m.recommended && (
                    <span
                      className="rounded"
                      style={{
                        fontSize: 9.5,
                        padding: "1px 5px",
                        background: "var(--accent-soft)",
                        color: "var(--accent-ink)",
                        fontWeight: 500,
                        letterSpacing: ".02em",
                      }}
                    >
                      REC
                    </span>
                  )}
                </div>
                <div
                  className="mt-0.5"
                  style={{ fontSize: 11, color: "var(--ink-3)" }}
                >
                  {m.desc} · {m.size}
                </div>
              </div>
              {m.name === selectedName && (
                <Check
                  className="h-3.5 w-3.5"
                  style={{ color: "var(--accent)" }}
                />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
