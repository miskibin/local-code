"use client"

import { Markdown } from "../Markdown"
import { DefaultResult } from "./default"
import type { ToolRenderer, ToolResultProps } from "./types"
import type { ToolStep } from "@/lib/types"

const SKILL_PATH_RE = /^\/([a-z0-9-]+)\/SKILL\.md$/

function getSkillName(step: ToolStep): string | null {
  const path = typeof step.args?.file_path === "string" ? step.args.file_path : ""
  const m = SKILL_PATH_RE.exec(path)
  return m ? m[1] : null
}

function getReadFileLabel(step: ToolStep): React.ReactNode | null {
  const skill = getSkillName(step)
  if (!skill) return null
  const status = step.status ?? "done"
  const verb =
    status === "running" ? "Loading" : status === "error" ? "Failed loading" : "Loaded"
  return (
    <>
      <span>{verb}</span>{" "}
      <code
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12.5,
          color: "var(--accent-ink)",
        }}
      >
        {skill}
      </code>{" "}
      <span style={{ color: "var(--ink-2)" }}>skill</span>
    </>
  )
}

/**
 * `read_file` returns content prefixed with right-padded line numbers and a
 * tab (deepagents `format_content_with_line_numbers`). Strip them so the
 * markdown body renders cleanly.
 */
function stripLineNumbers(raw: string): string {
  return raw
    .split("\n")
    .map((line) => {
      const m = /^\s*\d+\t(.*)$/.exec(line)
      return m ? m[1] : line
    })
    .join("\n")
}

function ReadFileResult({ result, status, step }: ToolResultProps) {
  if (!getSkillName(step)) {
    return <DefaultResult result={result} status={status} step={step} />
  }
  const body = stripLineNumbers(result || "").trim()
  // Drop the YAML frontmatter — already shown in the header / Skills tab.
  const withoutFrontmatter = body.replace(/^---\s*\n[\s\S]*?\n---\s*\n+/, "")
  return (
    <div
      className="rounded-lg px-3 py-2"
      style={{
        background: "var(--bg-soft)",
        border: "1px solid var(--border)",
      }}
    >
      <Markdown text={withoutFrontmatter} />
    </div>
  )
}

export const readFileRenderer: ToolRenderer = {
  getHeaderLabel: getReadFileLabel,
  hideArgs: true,
  Result: ReadFileResult,
}
