"use client"

import "./globals.css"

import { useEffect } from "react"

import ErrorState from "./_components/ErrorState"

export default function GlobalError({
  error,
  reset,
}: {
  error: unknown
  reset: () => void
}) {
  // Root-segment crashes bypass app/error.tsx, so this is the only place the
  // raw error object surfaces. Logging it preserves debuggability — without
  // this the user just sees a generic 500 with no console trail.
  useEffect(() => {
    console.error("global-error", error)
  }, [error])

  return (
    <html lang="en">
      <body data-app="local-chat">
        <ErrorState kind="500" onPrimary={reset} primaryHref="/" />
      </body>
    </html>
  )
}
