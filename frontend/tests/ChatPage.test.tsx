import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ChatPage from "@/app/_components/ChatPage";

vi.mock("@ai-sdk/react", () => ({
  useChat: () => ({
    messages: [{ id: "1", role: "user", parts: [{ type: "text", text: "hi" }] }],
    sendMessage: vi.fn(),
    status: "ready",
  }),
}));

describe("ChatPage", () => {
  it("renders user message text from parts", () => {
    render(<ChatPage />);
    expect(screen.getByText("hi")).toBeInTheDocument();
  });

  it("renders an input form", () => {
    render(<ChatPage />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });
});
