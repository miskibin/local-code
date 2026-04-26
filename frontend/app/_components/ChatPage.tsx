"use client";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useState } from "react";
import { nanoid } from "nanoid";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000/chat";

export default function ChatPage() {
  const [threadId] = useState(() => nanoid());
  const { messages, sendMessage, status } = useChat({
    id: threadId,
    transport: new DefaultChatTransport({ api: BACKEND_URL }),
  });
  const [input, setInput] = useState("");

  return (
    <div className="mx-auto flex h-dvh max-w-3xl flex-col gap-4 p-4">
      <div className="flex-1 overflow-y-auto space-y-3">
        {messages.map((m) => (
          <div key={m.id} className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">{m.role}</div>
            {m.parts.map((p, i) =>
              p.type === "text" ? <div key={i}>{p.text}</div> : null
            )}
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim()) return;
          sendMessage({ text: input });
          setInput("");
        }}
        className="flex gap-2"
      >
        <input
          aria-label="message"
          className="flex-1 rounded-md border px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={status === "streaming"}
        />
        <button type="submit" disabled={status === "streaming"} className="rounded-md border px-4">
          Send
        </button>
      </form>
    </div>
  );
}
