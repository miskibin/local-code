import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

import {
  AssistantMessage,
  formatTokens,
  formatDuration,
} from "@/app/_components/Messages"
import type { AssistantMsg } from "@/app/_components/Messages"

vi.mock("@/app/_components/ArtifactRefs", async () => {
  const actual = await vi.importActual<
    typeof import("@/app/_components/ArtifactRefs")
  >("@/app/_components/ArtifactRefs")
  return actual
})

const baseMsg = (overrides: Partial<AssistantMsg> = {}): AssistantMsg => ({
  id: "a1",
  contentBlocks: [{ type: "text", text: "hi there" }],
  ...overrides,
})

const baseProps = {
  expanded: {},
  toggleStep: () => {},
  isLast: true,
  streaming: false,
  savedArtifacts: {},
  onSaveArtifact: () => {},
  onOpenArtifact: () => {},
}

describe("formatTokens", () => {
  it("renders sub-1k counts as raw integers", () => {
    expect(formatTokens(0)).toBe("0")
    expect(formatTokens(42)).toBe("42")
    expect(formatTokens(999)).toBe("999")
  })

  it("renders 1k–10k counts with one decimal, dropping trailing zeros", () => {
    expect(formatTokens(1000)).toBe("1k")
    expect(formatTokens(1234)).toBe("1.2k")
    expect(formatTokens(9990)).toBe("10k")
  })

  it("rounds 10k+ counts to whole thousands", () => {
    expect(formatTokens(10_400)).toBe("10k")
    expect(formatTokens(125_600)).toBe("126k")
  })
})

describe("formatDuration", () => {
  it("renders sub-second times in ms", () => {
    expect(formatDuration(0)).toBe("0ms")
    expect(formatDuration(450)).toBe("450ms")
  })

  it("renders 1–60s times with one decimal, dropping trailing zeros", () => {
    expect(formatDuration(1000)).toBe("1s")
    expect(formatDuration(12_400)).toBe("12.4s")
  })

  it("renders minute+ times as `Xm Ys`", () => {
    expect(formatDuration(60_000)).toBe("1m")
    expect(formatDuration(75_500)).toBe("1m 16s")
    expect(formatDuration(125_000)).toBe("2m 5s")
  })
})

describe("AssistantMessage usage row", () => {
  it("renders nothing when usage is absent", () => {
    render(<AssistantMessage msg={baseMsg()} {...baseProps} />)
    expect(screen.queryByLabelText("Token usage")).toBeNull()
  })

  it("renders token counts and duration in a single subtle row", () => {
    render(
      <AssistantMessage
        msg={baseMsg({
          usage: { inputTokens: 1234, outputTokens: 56, durationMs: 12_400 },
        })}
        {...baseProps}
      />
    )
    const row = screen.getByLabelText("Token usage")
    expect(row.textContent).toContain("1.2k")
    expect(row.textContent).toContain("56")
    expect(row.textContent).toContain("12.4s")
  })

  it("hides duration when not provided (reload path)", () => {
    render(
      <AssistantMessage
        msg={baseMsg({
          usage: { inputTokens: 100, outputTokens: 20 },
        })}
        {...baseProps}
      />
    )
    const row = screen.getByLabelText("Token usage")
    expect(row.textContent).toContain("100")
    expect(row.textContent).toContain("20")
    expect(row.textContent).not.toMatch(/\d+s|\d+ms/)
  })

  it("hides zero-token columns instead of rendering `0`", () => {
    render(
      <AssistantMessage
        msg={baseMsg({
          usage: { inputTokens: 0, outputTokens: 42, durationMs: 500 },
        })}
        {...baseProps}
      />
    )
    const row = screen.getByLabelText("Token usage")
    expect(row.textContent).toContain("42")
    expect(row.textContent).toContain("500ms")
    // The "0" input count must not appear as a standalone token chip.
    const inputChip = row.querySelector('[title="Input tokens"]')
    expect(inputChip).toBeNull()
  })

  it("does not render the row while streaming (action bar is hidden then)", () => {
    render(
      <AssistantMessage
        msg={baseMsg({
          usage: { inputTokens: 5, outputTokens: 5, durationMs: 100 },
        })}
        {...baseProps}
        streaming={true}
      />
    )
    expect(screen.queryByLabelText("Token usage")).toBeNull()
  })
})
