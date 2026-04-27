import { describe, expect, it } from "vitest"
import { __testing__, type AnyPart } from "@/app/_components/ChatView"

const { partsToContentBlocks } = __testing__

function todosPart(opts: {
  callId: string
  todos: { content: string; status: "pending" | "in_progress" | "completed" }[]
  state?: string
  output?: unknown
}): AnyPart {
  return {
    type: "tool-write_todos",
    toolCallId: opts.callId,
    toolName: "write_todos",
    state:
      opts.state ??
      (opts.output !== undefined ? "output-available" : "input-available"),
    input: { todos: opts.todos },
    output: opts.output,
  }
}

function fetchPart(opts: {
  callId: string
  url: string
  output?: string
}): AnyPart {
  return {
    type: "tool-web_fetch",
    toolCallId: opts.callId,
    toolName: "web_fetch",
    state: opts.output !== undefined ? "output-available" : "input-available",
    input: { url: opts.url },
    output: opts.output,
  }
}

describe("partsToContentBlocks — plan handling", () => {
  it("collapses multiple write_todos calls into a single plan block using the latest todos", () => {
    const blocks = partsToContentBlocks([
      todosPart({
        callId: "wt_1",
        todos: [
          { content: "Search", status: "pending" },
          { content: "Fetch", status: "pending" },
          { content: "Cross-ref", status: "pending" },
          { content: "Synthesize", status: "pending" },
        ],
        output: "ok",
      }),
      fetchPart({ callId: "f_1", url: "https://x", output: "page" }),
      todosPart({
        callId: "wt_2",
        todos: [
          { content: "Search", status: "completed" },
          { content: "Fetch", status: "completed" },
          { content: "Cross-ref", status: "pending" },
          { content: "Synthesize", status: "pending" },
        ],
        output: "ok",
      }),
    ])

    const planBlocks = blocks.filter((b) => b.type === "plan")
    expect(planBlocks).toHaveLength(1)
    if (planBlocks[0].type === "plan") {
      expect(planBlocks[0].todos).toHaveLength(4)
      expect(planBlocks[0].todos[0].status).toBe("completed")
      expect(planBlocks[0].todos[2].status).toBe("pending")
      expect(planBlocks[0].streaming).toBe(false)
    }
    // The plan block sits at the position of the first write_todos call —
    // before the web_fetch step.
    expect(blocks[0].type).toBe("plan")
    expect(blocks[1].type).toBe("step")
    if (blocks[1].type === "step") {
      expect(blocks[1].step.kind).toBe("tool")
      if (blocks[1].step.kind === "tool") {
        expect(blocks[1].step.tool).toBe("web_fetch")
      }
    }
  })

  it("marks plan as streaming when the latest write_todos has not produced output yet", () => {
    const blocks = partsToContentBlocks([
      todosPart({
        callId: "wt_1",
        todos: [{ content: "Step A", status: "pending" }],
        output: "ok",
      }),
      todosPart({
        callId: "wt_2",
        todos: [{ content: "Step A", status: "in_progress" }],
        // no output → state stays at input-available
      }),
    ])

    const planBlocks = blocks.filter((b) => b.type === "plan")
    expect(planBlocks).toHaveLength(1)
    if (planBlocks[0].type === "plan") {
      expect(planBlocks[0].todos[0].status).toBe("in_progress")
      expect(planBlocks[0].streaming).toBe(true)
    }
  })

  it("places the plan block between text segments at the first write_todos position", () => {
    const blocks = partsToContentBlocks([
      { type: "text", text: "Starting up..." } as AnyPart,
      todosPart({
        callId: "wt_1",
        todos: [{ content: "Do thing", status: "pending" }],
        output: "ok",
      }),
      { type: "text", text: "All done." } as AnyPart,
    ])

    expect(blocks).toHaveLength(3)
    expect(blocks[0]).toEqual({ type: "text", text: "Starting up..." })
    expect(blocks[1].type).toBe("plan")
    expect(blocks[2]).toEqual({ type: "text", text: "All done." })
  })

  it("does not emit a plan block when write_todos has no todos", () => {
    const blocks = partsToContentBlocks([
      {
        type: "tool-write_todos",
        toolCallId: "wt_1",
        toolName: "write_todos",
        state: "input-available",
        input: { todos: [] },
      } as AnyPart,
    ])
    expect(blocks.filter((b) => b.type === "plan")).toHaveLength(0)
  })

  it("renders the plan block above the subagent that produced it", () => {
    // task dispatcher parent + write_todos child (subagent's own plan).
    // Stream order: task input → write_todos input/output → task output. The
    // child's stream position sits after the parent's, so we must hoist the
    // plan to the parent's position rather than emit it at the child.
    const subagentMeta = {
      subagent: {
        parentToolCallId: "task_1",
        namespace: ["subagent:sql_agent"],
      },
    }
    const blocks = partsToContentBlocks([
      {
        type: "tool-task",
        toolCallId: "task_1",
        toolName: "task",
        state: "output-available",
        input: {
          subagent_type: "sql_agent",
          description: "Inspect the Chinook database schema",
        },
        output: "schema markdown",
      } as AnyPart,
      {
        type: "tool-write_todos",
        toolCallId: "wt_child",
        toolName: "write_todos",
        state: "output-available",
        input: {
          todos: [
            { content: "Retrieve schema", status: "completed" },
            { content: "Format markdown", status: "completed" },
          ],
        },
        output: "ok",
        callProviderMetadata: subagentMeta,
        resultProviderMetadata: subagentMeta,
      } as AnyPart,
    ])

    expect(blocks).toHaveLength(2)
    expect(blocks[0].type).toBe("plan")
    if (blocks[0].type === "plan") {
      expect(blocks[0].todos).toHaveLength(2)
    }
    expect(blocks[1].type).toBe("step")
    if (blocks[1].type === "step") {
      expect(blocks[1].step.kind).toBe("subagent")
      if (blocks[1].step.kind === "subagent") {
        expect(blocks[1].step.agent.id).toBe("sql_agent")
      }
    }
  })

  it("matches dynamic-tool parts with toolName='write_todos'", () => {
    const blocks = partsToContentBlocks([
      {
        type: "dynamic-tool",
        toolCallId: "wt_1",
        toolName: "write_todos",
        state: "output-available",
        input: { todos: [{ content: "X", status: "completed" }] },
        output: "ok",
      } as AnyPart,
    ])
    expect(blocks).toHaveLength(1)
    expect(blocks[0].type).toBe("plan")
  })
})
