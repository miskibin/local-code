"use client"

import { Check, CircleHelp, Loader2 } from "lucide-react"
import { useState } from "react"

export type QuizCardProps = {
  toolCallId: string
  question: string
  options: string[]
  allowCustom: boolean
  status: "running" | "done" | "error"
  answer?: string
  onSubmit?: (toolCallId: string, value: string) => void
}

const LETTERS = ["A", "B", "C", "D", "E", "F"]

export function QuizCard({
  toolCallId,
  question,
  options,
  allowCustom,
  status,
  answer,
  onSubmit,
}: QuizCardProps) {
  const [picked, setPicked] = useState<number | null>(null)
  const [custom, setCustom] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const isAnswered = status !== "running" || !!answer

  const customIdx = options.length
  const isCustomPicked = allowCustom && picked === customIdx
  const value = isCustomPicked
    ? custom.trim()
    : picked != null
      ? options[picked]
      : ""
  const canSubmit = !isAnswered && !submitting && value.length > 0 && !!onSubmit

  const submit = () => {
    if (!canSubmit || !onSubmit) return
    setSubmitting(true)
    onSubmit(toolCallId, value)
  }

  return (
    <div
      className="lc-reveal my-1.5 mb-3.5 overflow-hidden rounded-xl"
      style={{
        border: "1px solid var(--tool-border)",
        background: "#fff",
      }}
    >
      <div
        className="flex items-center gap-2 px-3.5 py-2.5"
        style={{
          background: isAnswered ? "var(--accent-soft)" : "var(--amber-soft)",
          borderBottom: "1px solid var(--tool-border)",
          color: "var(--ink)",
        }}
      >
        <CircleHelp
          className="h-4 w-4"
          style={{ color: isAnswered ? "var(--accent)" : "var(--amber)" }}
        />
        <span className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>
          Asking
        </span>
        <code
          className="font-medium"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            color: isAnswered ? "var(--accent-ink)" : "var(--amber)",
          }}
        >
          quiz
        </code>
        <span
          className="rounded-md px-1.5 py-0.5"
          style={{
            fontSize: 11.5,
            color: "var(--ink-3)",
            fontFamily: "var(--font-mono)",
            background: "#fff",
            border: "1px solid var(--border)",
          }}
        >
          human
        </span>
        <span
          className="ml-auto inline-flex items-center gap-1.5 rounded-full px-2 py-0.5"
          style={{
            fontSize: 11.5,
            background: isAnswered ? "var(--accent-soft)" : "#fff",
            border: `1px solid ${isAnswered ? "var(--accent)" : "var(--amber)"}`,
            color: isAnswered ? "var(--accent-ink)" : "var(--amber)",
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background: isAnswered ? "var(--accent)" : "var(--amber)",
            }}
          />
          {isAnswered ? "Answered" : "Awaiting your answer"}
        </span>
      </div>

      <div className="px-4 pt-3 pb-2">
        <div
          className="mb-1 uppercase"
          style={{
            fontSize: 11,
            color: "var(--ink-3)",
            letterSpacing: ".04em",
          }}
        >
          Question
        </div>
        <div
          className="mb-3 text-[15px] font-medium"
          style={{ color: "var(--ink)" }}
        >
          {question}
        </div>

        <div className="flex flex-col gap-1.5">
          {options.map((opt, i) => (
            <Option
              key={i}
              letter={LETTERS[i] ?? String(i + 1)}
              label={opt}
              selected={picked === i}
              answered={isAnswered && answer === opt}
              disabled={isAnswered}
              onPick={() => !isAnswered && setPicked(i)}
            />
          ))}
          {allowCustom && (
            <CustomOption
              letter={LETTERS[customIdx] ?? "?"}
              selected={isCustomPicked}
              answered={
                isAnswered && !!answer && !options.includes(answer)
              }
              disabled={isAnswered}
              value={isAnswered ? (answer ?? "") : custom}
              onPick={() => !isAnswered && setPicked(customIdx)}
              onChange={(v) => {
                if (isAnswered) return
                setCustom(v)
                setPicked(customIdx)
              }}
            />
          )}
        </div>
      </div>

      <div
        className="flex items-center justify-between gap-3 px-4 py-2.5"
        style={{
          borderTop: "1px solid var(--tool-border)",
          background: "var(--bg-soft)",
        }}
      >
        <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>
          {isAnswered
            ? "Answer submitted."
            : allowCustom
              ? "Pick an option, or write your own."
              : "Pick an option."}
        </span>
        {!isAnswered && (
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit}
            className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] text-white"
            style={{
              background: canSubmit ? "var(--accent)" : "var(--hover-strong)",
              border: 0,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {submitting ? (
              <Loader2 className="lc-spin h-3.5 w-3.5" />
            ) : null}
            Submit answer ›
          </button>
        )}
      </div>
    </div>
  )
}

function Option({
  letter,
  label,
  selected,
  answered,
  disabled,
  onPick,
}: {
  letter: string
  label: string
  selected: boolean
  answered: boolean
  disabled: boolean
  onPick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onPick}
      disabled={disabled}
      className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left transition"
      style={{
        background: answered ? "var(--accent-soft)" : "#fff",
        border: `1px solid ${selected || answered ? "var(--accent)" : "var(--border)"}`,
        cursor: disabled ? "default" : "pointer",
        color: "var(--ink)",
      }}
    >
      <span
        className="grid h-4 w-4 flex-shrink-0 place-items-center rounded-full"
        style={{
          border: `1.5px solid ${selected || answered ? "var(--accent)" : "var(--border)"}`,
          background: selected || answered ? "var(--accent)" : "transparent",
        }}
      >
        {answered ? (
          <Check className="h-2.5 w-2.5" style={{ color: "#fff" }} />
        ) : selected ? (
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: "#fff" }}
          />
        ) : null}
      </span>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          color: "var(--ink-3)",
          minWidth: 14,
        }}
      >
        {letter}
      </span>
      <span className="text-[14px]">{label}</span>
    </button>
  )
}

function CustomOption({
  letter,
  selected,
  answered,
  disabled,
  value,
  onPick,
  onChange,
}: {
  letter: string
  selected: boolean
  answered: boolean
  disabled: boolean
  value: string
  onPick: () => void
  onChange: (v: string) => void
}) {
  const active = selected || answered
  return (
    <div
      onClick={onPick}
      className="flex items-start gap-3 rounded-lg px-3 py-2.5 transition"
      style={{
        background: answered ? "var(--accent-soft)" : "#fff",
        border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
        cursor: disabled ? "default" : "text",
      }}
    >
      <span
        className="mt-0.5 grid h-4 w-4 flex-shrink-0 place-items-center rounded-full"
        style={{
          border: `1.5px solid ${active ? "var(--accent)" : "var(--border)"}`,
          background: active ? "var(--accent)" : "transparent",
        }}
      >
        {answered ? (
          <Check className="h-2.5 w-2.5" style={{ color: "#fff" }} />
        ) : selected ? (
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: "#fff" }}
          />
        ) : null}
      </span>
      <span
        className="mt-0.5"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          color: "var(--ink-3)",
          minWidth: 14,
        }}
      >
        {letter}
      </span>
      <div className="flex flex-1 flex-col gap-1">
        <span className="text-[14px]" style={{ color: "var(--ink)" }}>
          Type your own answer
        </span>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Write a custom answer…"
          rows={1}
          className="resize-none bg-transparent outline-none"
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 13,
            color: "var(--ink-2)",
            minHeight: 20,
          }}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  )
}
