"use client"

import "./globals.css"

import ErrorState from "./_components/ErrorState"

export default function GlobalError({
  unstable_retry,
}: {
  error: unknown
  unstable_retry: () => void
}) {
  return (
    <html lang="en">
      <body data-app="local-chat">
        <ErrorState kind="500" onPrimary={unstable_retry} primaryHref="/" />
      </body>
    </html>
  )
}
