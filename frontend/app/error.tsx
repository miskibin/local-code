"use client"

import { useEffect } from "react"

import ErrorState from "./_components/ErrorState"

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return <ErrorState kind="500" onPrimary={reset} primaryHref="/" />
}
