"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth"

const ssoProviders = [
  { id: "okta", label: "Continue with Okta", subtitle: "WORK · SAML", icon: "○" },
  {
    id: "google",
    label: "Continue with Google Workspace",
    subtitle: "WORK · OIDC",
    icon: "G",
  },
  {
    id: "microsoft",
    label: "Continue with Microsoft Entra",
    subtitle: "WORK · OIDC",
    icon: "▦",
  },
  { id: "github", label: "Continue with GitHub", subtitle: "OAUTH", icon: "" },
]

export default function LoginPage() {
  const { login } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.includes("@")) {
      toast.error("Enter a valid email")
      return
    }
    setSubmitting(true)
    try {
      await login(email)
      router.replace("/")
    } catch (err) {
      toast.error("Sign-in failed", { description: String(err) })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main
      className="relative flex min-h-dvh w-full flex-col"
      style={{
        background:
          "var(--bg, oklch(0.985 0 0)) repeating-linear-gradient(0deg, transparent 0 39px, var(--border) 39px 40px), repeating-linear-gradient(90deg, transparent 0 39px, var(--border) 39px 40px)",
      }}
    >
      <header className="flex w-full items-center justify-between px-8 py-6 text-xs tracking-wide">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <span className="grid size-7 place-items-center rounded-md bg-emerald-100 text-emerald-700">
            ✦
          </span>
          Local Chat
        </div>
        <div className="text-muted-foreground flex items-center gap-2 uppercase">
          <span className="size-1.5 rounded-full bg-emerald-500" />
          Workspace · auto-code
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <p className="text-muted-foreground mb-2 text-xs tracking-[0.18em] uppercase">
            Sign in
          </p>
          <h1 className="font-serif text-4xl tracking-tight">
            Continue to Local Chat
          </h1>
          <p className="text-muted-foreground mt-3 text-sm">
            Use your email to access local models, tasks, and saved artifacts.
            No password required for local development.
          </p>

          <form
            onSubmit={onSubmit}
            className="bg-card mt-8 flex flex-col gap-3 rounded-xl border p-4 shadow-sm"
          >
            <label className="text-xs tracking-wide uppercase" htmlFor="email">
              Work email
            </label>
            <Input
              id="email"
              type="email"
              autoFocus
              autoComplete="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
            />
            <Button type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Continue"}
            </Button>
          </form>

          <div className="mt-6 grid gap-2">
            {ssoProviders.map((p) => (
              <button
                key={p.id}
                type="button"
                disabled
                title="Demo — use email above"
                className="bg-card hover:bg-card flex w-full cursor-not-allowed items-center justify-between rounded-xl border p-4 text-left opacity-60"
              >
                <div className="flex items-center gap-3">
                  <span className="grid size-8 place-items-center rounded-md border text-base">
                    {p.icon}
                  </span>
                  <div>
                    <div className="text-sm font-medium">{p.label}</div>
                    <div className="text-muted-foreground text-[11px] tracking-wider uppercase">
                      {p.subtitle}
                    </div>
                  </div>
                </div>
                <span className="text-muted-foreground">›</span>
              </button>
            ))}
          </div>

          <div className="bg-card text-muted-foreground mt-6 flex items-start gap-3 rounded-xl border p-4 text-xs">
            <span className="text-emerald-600">⊙</span>
            <span>
              Email-only sign-in for local development. SSO buttons are mocked
              — pick any email to identify your sessions, tasks, and artifacts.
            </span>
          </div>

          <div className="text-muted-foreground mt-6 flex justify-between text-xs">
            <span>
              No SSO? <span className="underline">Request access</span>
            </span>
            <span className="space-x-3">
              <span>Privacy</span>
              <span>·</span>
              <span>Terms</span>
            </span>
          </div>
        </div>
      </div>
    </main>
  )
}
