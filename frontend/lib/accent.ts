export type AccentName = "blue" | "violet" | "emerald" | "rose"

export const ACCENTS: Record<AccentName, { label: string; color: string }> = {
  blue: { label: "Blue", color: "#2563eb" },
  violet: { label: "Violet", color: "#7c3aed" },
  emerald: { label: "Emerald", color: "#10b981" },
  rose: { label: "Rose", color: "#e11d48" },
}

export const DEFAULT_ACCENT: AccentName = "blue"
export const ACCENT_STORAGE_KEY = "lc-accent"

export function applyAccent(name: AccentName) {
  const color = ACCENTS[name]?.color ?? ACCENTS[DEFAULT_ACCENT].color
  document.body.style.setProperty("--accent", color)
}

export function getStoredAccent(): AccentName {
  if (typeof window === "undefined") return DEFAULT_ACCENT
  const v = localStorage.getItem(ACCENT_STORAGE_KEY) as AccentName | null
  return v && v in ACCENTS ? v : DEFAULT_ACCENT
}

export function setStoredAccent(name: AccentName) {
  localStorage.setItem(ACCENT_STORAGE_KEY, name)
  applyAccent(name)
}
