"use client";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useEffect, useRef, useState } from "react";
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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight });
    }
  }, [messages]);

  const busy = status === "streaming" || status === "submitted";

  return (
    <div className="flex h-dvh flex-col bg-white text-zinc-900">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 pt-10 pb-40">
          {messages.length === 0 ? (
            <div className="flex h-[60dvh] items-center justify-center text-2xl text-zinc-500">
              What are you working on?
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) =>
                m.role === "user" ? (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[80%] rounded-3xl bg-zinc-100 px-4 py-2 whitespace-pre-wrap">
                      {m.parts.map((p, i) =>
                        p.type === "text" ? <span key={i}>{p.text}</span> : null,
                      )}
                    </div>
                  </div>
                ) : (
                  <div key={m.id} className="whitespace-pre-wrap leading-relaxed">
                    {m.parts.map((p, i) =>
                      p.type === "text" ? <span key={i}>{p.text}</span> : null,
                    )}
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </div>
      <div className="border-t border-zinc-200/0 bg-gradient-to-t from-white to-white/0 pb-6 pt-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!input.trim() || busy) return;
            sendMessage({ text: input });
            setInput("");
          }}
          className="mx-auto w-full max-w-3xl px-4"
        >
          <div className="flex items-end gap-2 rounded-3xl border border-zinc-200 bg-white px-5 py-3 shadow-sm focus-within:border-zinc-300">
            <input
              aria-label="message"
              placeholder="Ask anything"
              className="flex-1 bg-transparent text-base outline-none placeholder:text-zinc-400"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              aria-label="Send"
              className="grid h-8 w-8 place-items-center rounded-full bg-zinc-900 text-white transition disabled:bg-zinc-300"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 19V5" />
                <path d="m5 12 7-7 7 7" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
