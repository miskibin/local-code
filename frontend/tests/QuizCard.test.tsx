import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"

import { QuizCard } from "@/app/_components/QuizCard"

const baseProps = {
  toolCallId: "tc1",
  question: "Pick one",
  options: ["A", "B", "C"],
  allowCustom: true,
  status: "running" as const,
}

describe("QuizCard answered collapse", () => {
  it("shows a compact summary and hides option rows", () => {
    render(
      <QuizCard
        {...baseProps}
        question="Pick table"
        options={["Album", "Artist", "Customer"]}
        status="done"
        answer="Artist"
        onSubmit={vi.fn()}
      />
    )
    expect(screen.getByText("Pick table")).toBeInTheDocument()
    const summaryLine = screen.getByText("Artist").closest("p")
    expect(summaryLine?.textContent?.replace(/\s/g, " ")).toMatch(
      /B\s*·\s*Artist/
    )
    expect(screen.queryByText("Submit answer ›")).toBeNull()
    expect(screen.queryByText("Question")).toBeNull()
    expect(screen.queryAllByRole("button")).toHaveLength(0)
  })
})

describe("QuizCard custom option", () => {
  it("does not render the 'Type your own answer' header", () => {
    render(<QuizCard {...baseProps} onSubmit={vi.fn()} />)
    expect(screen.queryByText("Type your own answer")).toBeNull()
  })

  it("accepts spaces typed into the custom textarea", async () => {
    const onSubmit = vi.fn()
    render(<QuizCard {...baseProps} onSubmit={onSubmit} />)

    const ta = screen.getByPlaceholderText(
      "Write a custom answer…"
    ) as HTMLTextAreaElement
    await userEvent.click(ta)
    await userEvent.type(ta, "trawa jest czerwona")
    expect(ta.value).toBe("trawa jest czerwona")

    await userEvent.click(screen.getByText("Submit answer ›"))
    expect(onSubmit).toHaveBeenCalledWith("tc1", "trawa jest czerwona")
  })

  it("space pressed on the radio wrapper still selects the custom option", async () => {
    render(<QuizCard {...baseProps} onSubmit={vi.fn()} />)
    const radio = screen.getByRole("radio")
    radio.focus()
    await userEvent.keyboard(" ")
    expect(radio).toHaveAttribute("aria-checked", "true")
  })
})
