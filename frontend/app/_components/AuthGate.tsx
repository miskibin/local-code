"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"
import { FirstLoginDialog } from "@/app/_components/FirstLoginDialog"
import { useAuth } from "@/lib/auth"

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const onLogin = pathname === "/login"

  useEffect(() => {
    if (!ready) return
    if (!user && !onLogin) {
      router.replace("/login")
      return
    }
    if (user && onLogin) {
      router.replace("/")
    }
  }, [ready, user, onLogin, router])

  if (!ready) return null
  if (!user && !onLogin) return null
  if (user && onLogin) return null
  return (
    <>
      {children}
      <FirstLoginDialog />
    </>
  )
}
