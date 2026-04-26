import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

const sendMessage = vi.fn();
const regenerate = vi.fn();
const setMessages = vi.fn();
const stop = vi.fn();

let mockMessages: Array<{
  id: string;
  role: "user" | "assistant";
  parts: Array<{ type: "text"; text: string }>;
}> = [];

vi.mock("@ai-sdk/react", () => ({
  useChat: () => ({
    messages: mockMessages,
    sendMessage,
    regenerate,
    setMessages,
    stop,
    status: "ready",
  }),
}));

vi.mock("ai", () => ({
  DefaultChatTransport: class {
    constructor(_: unknown) {}
  },
}));

vi.mock("@/lib/api", () => ({
  api: { getMessages: () => new Promise(() => {}) },
  CHAT_URL: "http://test/chat",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(""),
}));

import { ChatView } from "@/app/_components/ChatView";

const baseProps = {
  sessionId: "s1",
  onFirstUserMessage: vi.fn(),
  savedArtifacts: {},
  onSaveArtifact: vi.fn(),
  onOpenArtifact: vi.fn(),
};

describe("ChatView regenerate + edit", () => {
  beforeEach(() => {
    sendMessage.mockReset();
    regenerate.mockReset();
    setMessages.mockReset();
    mockMessages = [
      {
        id: "u1",
        role: "user",
        parts: [{ type: "text", text: "what's 2+2?" }],
      },
      {
        id: "a1",
        role: "assistant",
        parts: [{ type: "text", text: "4" }],
      },
    ];
  });

  it("regenerate button calls regenerate with assistant id", async () => {
    render(<ChatView {...baseProps} />);
    await userEvent.click(screen.getByTitle("Regenerate"));
    expect(regenerate).toHaveBeenCalledWith({ messageId: "a1" });
  });

  it("edit user message truncates and re-sends with reset", async () => {
    render(<ChatView {...baseProps} />);
    await userEvent.click(screen.getByTitle("Edit message"));
    const ta = await screen.findByDisplayValue("what's 2+2?");
    await userEvent.clear(ta);
    await userEvent.type(ta, "what's 5+5?");
    await userEvent.click(screen.getByText("Send"));

    expect(setMessages).toHaveBeenCalledTimes(1);
    const updater = setMessages.mock.calls[0][0] as (
      prev: typeof mockMessages,
    ) => typeof mockMessages;
    expect(updater(mockMessages)).toEqual([]);
    expect(sendMessage).toHaveBeenCalledWith(
      { text: "what's 5+5?" },
      { body: { reset: true } },
    );
  });

  it("cancel edit does not send", async () => {
    render(<ChatView {...baseProps} />);
    await userEvent.click(screen.getByTitle("Edit message"));
    await userEvent.click(screen.getByText("Cancel"));
    expect(sendMessage).not.toHaveBeenCalled();
    expect(setMessages).not.toHaveBeenCalled();
  });
});
