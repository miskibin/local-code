export type FontPreset = "mono" | "sans" | "system" | "serif"

export const FONT_PRESETS: Record<
  FontPreset,
  { label: string; stack: string }
> = {
  mono: {
    label: "Mono",
    stack:
      'var(--font-mono), ui-monospace, "Cascadia Code", "Consolas", monospace',
  },
  sans: {
    label: "Sans",
    stack: 'var(--font-sans-ui), ui-sans-serif, system-ui, sans-serif',
  },
  system: {
    label: "System",
    stack:
      'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  serif: {
    label: "Serif",
    stack: "var(--font-serif), ui-serif, Georgia, serif",
  },
}

export const DEFAULT_FONT_PRESET: FontPreset = "mono"
export const FONT_STORAGE_KEY = "lc-font"

export function applyFontPreset(name: FontPreset) {
  const stack =
    FONT_PRESETS[name]?.stack ?? FONT_PRESETS[DEFAULT_FONT_PRESET].stack
  document.documentElement.style.setProperty("--lc-body-font", stack)
}

export function getStoredFontPreset(): FontPreset {
  if (typeof window === "undefined") return DEFAULT_FONT_PRESET
  const v = localStorage.getItem(FONT_STORAGE_KEY) as FontPreset | null
  return v && v in FONT_PRESETS ? v : DEFAULT_FONT_PRESET
}

export function setStoredFontPreset(name: FontPreset) {
  localStorage.setItem(FONT_STORAGE_KEY, name)
  applyFontPreset(name)
}
