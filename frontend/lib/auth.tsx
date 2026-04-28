"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

const STORAGE_KEY = "lc-user-email"
const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL_BASE ?? "http://localhost:8000"

export type User = { id: string; email: string; is_admin: boolean }

type AuthState = {
  user: User | null
  ready: boolean
  login: (email: string) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function readAuthEmail(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(STORAGE_KEY)
}

export function authHeaders(): Record<string, string> {
  const email = readAuthEmail()
  return email ? { "X-User-Email": email } : {}
}

async function callLogin(email: string): Promise<User> {
  const r = await fetch(`${BACKEND}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
  if (!r.ok) throw new Error(`login failed: ${r.status} ${r.statusText}`)
  return (await r.json()) as User
}

async function fetchMe(email: string): Promise<User | null> {
  const r = await fetch(`${BACKEND}/auth/me`, {
    headers: { "X-User-Email": email },
  })
  if (!r.ok) return null
  return (await r.json()) as User
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  /* eslint-disable react-hooks/set-state-in-effect -- sync from localStorage / network on mount */
  useEffect(() => {
    const email = readAuthEmail()
    if (!email) {
      setReady(true)
      return
    }
    fetchMe(email)
      .then((u) => setUser(u))
      .finally(() => setReady(true))
  }, [])
  /* eslint-enable react-hooks/set-state-in-effect */

  const login = useCallback(async (email: string) => {
    const trimmed = email.trim().toLowerCase()
    const u = await callLogin(trimmed)
    window.localStorage.setItem(STORAGE_KEY, u.email)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (ctx === null) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}

/** Tolerant variant for places (tests, isolated components) that may render
 * outside AuthProvider. Returns null when no provider is mounted. */
export function useAuthOptional(): AuthState | null {
  return useContext(AuthContext)
}
