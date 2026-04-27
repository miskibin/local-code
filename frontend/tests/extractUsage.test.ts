import { describe, expect, it } from "vitest"

import { __testing__, type AnyPart } from "@/app/_components/ChatView"

const { extractUsage } = __testing__

describe("extractUsage", () => {
  it("returns null when no data-usage part is present", () => {
    const parts: AnyPart[] = [
      { type: "text", text: "hi" },
      { type: "tool-web_fetch", toolCallId: "c1" },
    ]
    expect(extractUsage(parts)).toBeNull()
  })

  it("returns the usage payload from a data-usage part", () => {
    const parts: AnyPart[] = [
      { type: "text", text: "hi" },
      {
        type: "data-usage",
        id: "usage_msg_1",
        data: { inputTokens: 12, outputTokens: 5, durationMs: 4200 },
      },
    ]
    expect(extractUsage(parts)).toEqual({
      inputTokens: 12,
      outputTokens: 5,
      durationMs: 4200,
    })
  })

  it("prefers the latest data-usage part when more than one is present", () => {
    const parts: AnyPart[] = [
      {
        type: "data-usage",
        id: "u1",
        data: { inputTokens: 1, outputTokens: 1 },
      },
      {
        type: "data-usage",
        id: "u2",
        data: { inputTokens: 99, outputTokens: 7, durationMs: 1000 },
      },
    ]
    expect(extractUsage(parts)).toEqual({
      inputTokens: 99,
      outputTokens: 7,
      durationMs: 1000,
    })
  })

  it("ignores malformed data-usage parts (no data field)", () => {
    const parts: AnyPart[] = [{ type: "data-usage" }]
    expect(extractUsage(parts)).toBeNull()
  })
})
