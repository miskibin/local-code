import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToolCall } from "@/app/_components/ToolCall";
import { getToolRenderer } from "@/app/_components/tools";
import type { ToolStep } from "@/lib/types";

const baseStep: ToolStep = {
  kind: "tool",
  tool: "python_exec",
  server: "local",
  args: { code: "print(1+1)" },
  result: "2",
  status: "done",
};

describe("tool renderer registry", () => {
  it("returns custom renderer for python_exec", () => {
    const r = getToolRenderer("python_exec");
    expect(r.Args).toBeDefined();
    expect(r.Result).toBeDefined();
  });

  it("returns empty config for unknown tool (default fallback)", () => {
    const r = getToolRenderer("totally_made_up_tool");
    expect(r.Args).toBeUndefined();
    expect(r.Result).toBeUndefined();
  });

  it("ToolCall renders python_exec args via custom renderer", async () => {
    render(<ToolCall step={baseStep} expanded={true} onToggle={vi.fn()} />);
    expect(screen.getByText(/Arguments/i)).toBeInTheDocument();
    expect(screen.getByText(/Result/i)).toBeInTheDocument();
    expect(screen.getByText(/python_exec/)).toBeInTheDocument();
  });

  it("ToolCall renders header chrome regardless of tool", async () => {
    const u = userEvent.setup();
    const onToggle = vi.fn();
    const unknownStep: ToolStep = { ...baseStep, tool: "unknown_tool" };
    render(<ToolCall step={unknownStep} expanded={false} onToggle={onToggle} />);
    expect(screen.getByText(/Called/)).toBeInTheDocument();
    expect(screen.getByText(/unknown_tool/)).toBeInTheDocument();
    await u.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalled();
  });
});
