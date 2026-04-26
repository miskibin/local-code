import { describe, expect, it } from "vitest";
import {
  __testing__,
  type AnyPart,
} from "@/app/_components/ChatView";

const { partsToContentBlocks } = __testing__;

function toolPart(opts: {
  callId: string;
  toolName: string;
  input: unknown;
  output?: unknown;
  state?: string;
  parentId?: string;
}): AnyPart {
  const subagent: Record<string, unknown> = {};
  if (opts.parentId) {
    subagent.parentToolCallId = opts.parentId;
    subagent.namespace = ["subagent:research"];
  }
  const meta = opts.parentId ? { subagent } : undefined;
  return {
    type: `tool-${opts.toolName}`,
    toolCallId: opts.callId,
    state: opts.state ?? (opts.output !== undefined ? "output-available" : "input-available"),
    input: opts.input,
    output: opts.output,
    callProviderMetadata: meta,
    resultProviderMetadata: meta,
  };
}

describe("partsToContentBlocks", () => {
  it("renders a flat tool call when there are no children", () => {
    const blocks = partsToContentBlocks([
      toolPart({ callId: "c1", toolName: "python_exec", input: { code: "1+1" }, output: "2" }),
    ]);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].type).toBe("step");
    if (blocks[0].type === "step") {
      expect(blocks[0].step.kind).toBe("tool");
    }
  });

  it("groups child tools under a Subagent block when parent is a dispatcher", () => {
    const parts: AnyPart[] = [
      toolPart({
        callId: "task_1",
        toolName: "task",
        input: {
          subagent_type: "research-agent",
          description: "Research solar vs wind",
        },
        output: "research result",
      }),
      toolPart({
        callId: "inner_1",
        toolName: "web_fetch",
        input: { url: "https://x" },
        output: "page",
        parentId: "task_1",
      }),
      toolPart({
        callId: "inner_2",
        toolName: "web_fetch",
        input: { url: "https://y" },
        output: "page2",
        parentId: "task_1",
      }),
    ];

    const blocks = partsToContentBlocks(parts);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].type).toBe("step");
    if (blocks[0].type === "step") {
      const step = blocks[0].step;
      expect(step.kind).toBe("subagent");
      if (step.kind === "subagent") {
        expect(step.agent.id).toBe("research-agent");
        expect(step.agent.name).toBe("Research Agent");
        expect(step.task).toBe("Research solar vs wind");
        expect(step.steps).toHaveLength(2);
        expect(step.steps?.[0].tool).toBe("web_fetch");
        expect(step.steps?.[1].tool).toBe("web_fetch");
        expect(step.summary).toBe("research result");
      }
    }
  });

  it("interleaves text + subagent block in stream order", () => {
    const blocks = partsToContentBlocks([
      { type: "text", text: "Looking that up..." } as AnyPart,
      toolPart({
        callId: "task_1",
        toolName: "task",
        input: { subagent_type: "research-agent", description: "X" },
        output: "result",
      }),
      toolPart({
        callId: "inner_1",
        toolName: "web_fetch",
        input: { url: "https://x" },
        output: "page",
        parentId: "task_1",
      }),
      { type: "text", text: "Done." } as AnyPart,
    ]);
    expect(blocks).toHaveLength(3);
    expect(blocks[0]).toEqual({ type: "text", text: "Looking that up..." });
    expect(blocks[1].type).toBe("step");
    if (blocks[1].type === "step") expect(blocks[1].step.kind).toBe("subagent");
    expect(blocks[2]).toEqual({ type: "text", text: "Done." });
  });

  it("keeps children flat when their parent isn't in the parts (orphaned)", () => {
    // If parent metadata points at an id we don't have, fall back to flat.
    const blocks = partsToContentBlocks([
      toolPart({
        callId: "orphan",
        toolName: "web_fetch",
        input: { url: "https://x" },
        output: "page",
        parentId: "missing_parent",
      }),
    ]);
    expect(blocks).toHaveLength(1);
    if (blocks[0].type === "step") {
      expect(blocks[0].step.kind).toBe("tool");
    }
  });
});
