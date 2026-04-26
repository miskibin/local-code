"use client"

import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  const isDark = mounted && resolvedTheme === "dark"
  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="fixed top-3 right-3 z-50 grid h-9 w-9 place-items-center rounded-full transition hover:opacity-80"
      style={{
        background: "var(--bg-soft)",
        border: "1px solid var(--border)",
        color: "var(--ink-2)",
      }}
    >
      {mounted ? isDark ? <Sun size={16} /> : <Moon size={16} /> : null}
    </button>
  )
}
