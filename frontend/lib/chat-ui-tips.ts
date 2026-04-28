export const CHAT_UI_TIPS = [
  "Drag a chat in the sidebar onto pin or trash to organize threads.",
  "Theme, accent, and fonts live in Settings.",
  "Ask for presentations, tables, and other artifacts — the agent can build them.",
  "After a reply finishes, use the bookmark control to save the turn as a reusable task.",
] as const

/** Stable “pick” from the tips list for a given key (e.g. session id). */
export function chatUiTipForKey(key: string): string {
  let h = 0
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) >>> 0
  }
  return CHAT_UI_TIPS[h % CHAT_UI_TIPS.length]
}
