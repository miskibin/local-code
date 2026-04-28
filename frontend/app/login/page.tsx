"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth"

const ssoProviders = [
  { id: "okta", label: "Continue with Okta", subtitle: "WORK · SAML", icon: "○" },
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
      className="lc-login-bg relative flex min-h-dvh w-full flex-col"
      aria-labelledby="login-heading"
    >
      <header className="flex w-full items-center justify-between px-4 py-5 sm:px-8 sm:py-6">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-semibold transition-opacity hover:opacity-90"
        >
          <span className="grid size-7 place-items-center rounded-md bg-emerald-100 text-emerald-700">
            ✦
          </span>
          Local Chat
        </Link>
        <div className="text-muted-foreground hidden items-center gap-2 text-xs tracking-wide uppercase sm:flex">
          <span className="size-1.5 shrink-0 rounded-full bg-emerald-500" />
          Workspace · auto-code
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 pb-10 pt-4 sm:px-6 sm:py-12">
        <div className="w-full max-w-md">
          <p className="text-muted-foreground mb-2 text-xs tracking-[0.18em] uppercase">
            Sign in
          </p>
          <h1
            id="login-heading"
            className="font-serif text-3xl tracking-tight sm:text-4xl"
          >
            Continue to Local Chat
          </h1>
          <p className="text-muted-foreground mt-3 text-pretty text-sm leading-relaxed">
            Use your work email to access local models, tasks, and saved
            artifacts. No password in this dev build.
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
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Signing in…" : "Continue"}
            </Button>
          </form>

          <section
            className="mt-8"
            aria-label="Enterprise single sign-on (not connected)"
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="text-muted-foreground text-xs tracking-[0.18em] uppercase">
                Enterprise SSO
              </h2>
              <Badge variant="secondary" className="font-normal">
                Not connected
              </Badge>
            </div>
            <div className="grid gap-2">
              {ssoProviders.map((p) => (
                <div
                  key={p.id}
                  className="bg-card text-muted-foreground flex w-full items-center justify-between rounded-xl border border-dashed p-4 text-left"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      className="grid size-8 shrink-0 place-items-center rounded-md border text-base"
                      aria-hidden
                    >
                      {p.icon}
                    </span>
                    <div className="min-w-0">
                      <div className="text-foreground text-sm font-medium">
                        {p.label}
                      </div>
                      <div className="text-[11px] tracking-wider uppercase opacity-80">
                        {p.subtitle}
                      </div>
                    </div>
                  </div>
                  <span className="shrink-0 opacity-50" aria-hidden>
                    ›
                  </span>
                </div>
              ))}
            </div>
          </section>

          <aside className="bg-card text-muted-foreground mt-6 flex items-start gap-3 rounded-xl border p-4 text-xs leading-relaxed">
            <span className="text-emerald-600" aria-hidden>
              ⊙
            </span>
            <p>
              This page is for local development: sign in with any email to
              label your session. Wire Okta (or another IdP) when you deploy.
            </p>
          </aside>

          <footer className="text-muted-foreground mt-8 border-t border-border/50 pt-6 text-xs leading-relaxed">
            <p className="text-pretty">
              Need company SSO or access policies? Configure them in your
              deployment; this build only stores data locally.
            </p>
          </footer>
        </div>
      </div>
    </main>
  )
}
