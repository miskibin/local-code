import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { Sidebar } from "@/app/_components/Sidebar"

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
    onTrashSession: vi.fn(),
    onRenameSession: vi.fn(),
    onTogglePinSession: vi.fn(),
    artifacts: [],
    onOpenArtifact: vi.fn(),
    onDeleteArtifact: vi.fn(),
    onTrashArtifact: vi.fn(),
  }

  it("renders chat rows", () => {
    render(<Sidebar {...baseProps} />)
    expect(screen.getByText("Plan trip")).toBeInTheDocument()
  })

  it("calls onNew when New chat clicked", async () => {
    const onNew = vi.fn()
    render(<Sidebar {...baseProps} onNew={onNew} />)
    await userEvent.click(screen.getByText("New chat"))
    expect(onNew).toHaveBeenCalled()
  })

  it("collapsed view shows icon-only rail", () => {
    render(<Sidebar {...baseProps} collapsed={true} />)
    expect(screen.queryByText("New chat")).not.toBeInTheDocument()
    expect(screen.getByLabelText("New chat")).toBeInTheDocument()
  })

  it("offers Langfuse trace in the active chat row menu when url is set", async () => {
    const user = userEvent.setup()
    render(
      <Sidebar
        {...baseProps}
        langfuseTraceUrl="https://langfuse.example/t/1"
      />,
    )
    expect(screen.queryByText("Langfuse trace")).not.toBeInTheDocument()
    await user.hover(screen.getByText("Plan trip").closest("div")!)
    await user.click(screen.getByTitle("More"))
    expect(await screen.findByText("Langfuse trace")).toBeInTheDocument()
  })

  it("only the active session row offers Langfuse trace in the menu", async () => {
    const user = userEvent.setup()
    render(
      <Sidebar
        {...baseProps}
        activeId="s2"
        sessions={[
          { id: "s1", title: "One" },
          { id: "s2", title: "Two" },
        ]}
        langfuseTraceUrl="https://langfuse.example/t/1"
      />,
    )
    await user.hover(screen.getByText("One").closest("div")!)
    await user.click(screen.getAllByTitle("More")[0])
    expect(screen.queryByText("Langfuse trace")).not.toBeInTheDocument()
    await user.keyboard("{Escape}")
    await user.hover(screen.getByText("Two").closest("div")!)
    await user.click(screen.getAllByTitle("More")[1])
    expect(await screen.findByText("Langfuse trace")).toBeInTheDocument()
  })

  it("collapsed rail shows Langfuse when langfuseTraceUrl is set", () => {
    render(
      <Sidebar
        {...baseProps}
        collapsed={true}
        langfuseTraceUrl="https://langfuse.example/t/1"
      />,
    )
    expect(screen.getByLabelText("Open trace in Langfuse")).toBeInTheDocument()
  })
})
