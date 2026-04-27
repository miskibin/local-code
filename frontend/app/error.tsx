"use client"

import { useEffect } from "react"

import ErrorState from "./_components/ErrorState"

export default function ErrorBoundary({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return <ErrorState kind="500" onPrimary={unstable_retry} primaryHref="/" />
}
