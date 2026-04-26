import { describe, expect, it } from "vitest";

import { __testing__, type AnyPart } from "@/app/_components/ChatView";

const { extractArtifactIds } = __testing__;

describe("extractArtifactIds", () => {
  it("collects artifactId from data-artifact parts in stream order", () => {
    const parts: AnyPart[] = [
      { type: "text", text: "ok" },
      {
        type: "data-artifact",
        id: "art-1",
        data: {
          toolCallId: "call_a",
          artifactId: "art-1",
          kind: "table",
          title: "T",
          summary: "...",
          updatedAt: "2026-04-26T00:00:00Z",
        },
      },
      { type: "tool-python_exec", toolCallId: "call_a" },
      {
        type: "data-artifact",
        id: "art-2",
        data: {
          toolCallId: "call_b",
          artifactId: "art-2",
          kind: "chart",
          title: "C",
          summary: "...",
          updatedAt: "2026-04-26T00:00:01Z",
        },
      },
    ];
    expect(extractArtifactIds(parts)).toEqual(["art-1", "art-2"]);
  });

  it("ignores non-artifact data parts and malformed entries", () => {
    const parts: AnyPart[] = [
      { type: "data-other", data: { artifactId: "x" } },
      { type: "data-artifact", data: {} },
      { type: "data-artifact" },
    ];
    expect(extractArtifactIds(parts)).toEqual([]);
  });
});
