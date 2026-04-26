import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Sidebar } from "@/app/_components/Sidebar";

describe("Sidebar", () => {
  const baseProps = {
    collapsed: false,
    onToggle: vi.fn(),
    sessions: [{ id: "s1", title: "Plan trip" }],
    activeId: "s1",
    onSelect: vi.fn(),
    onNew: vi.fn(),
    onSearch: vi.fn(),
    onDeleteSession: vi.fn(),
    artifacts: [],
    onOpenArtifact: vi.fn(),
    modelName: "gemma4:e4b",
  };

  it("renders chats and demo entry", () => {
    render(<Sidebar {...baseProps} />);
    expect(screen.getByText("Plan trip")).toBeInTheDocument();
    expect(screen.getByText(/SQL Analyst/i)).toBeInTheDocument();
    expect(screen.getByText("gemma4:e4b")).toBeInTheDocument();
  });

  it("calls onNew when New chat clicked", async () => {
    const onNew = vi.fn();
    render(<Sidebar {...baseProps} onNew={onNew} />);
    await userEvent.click(screen.getByText("New chat"));
    expect(onNew).toHaveBeenCalled();
  });

  it("collapsed view shows icon-only rail", () => {
    render(<Sidebar {...baseProps} collapsed={true} />);
    expect(screen.queryByText("New chat")).not.toBeInTheDocument();
    expect(screen.getByLabelText("New chat")).toBeInTheDocument();
  });
});
