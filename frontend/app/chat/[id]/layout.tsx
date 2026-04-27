import { Suspense } from "react"
import { ChatShell } from "@/app/_components/ChatShell"

export default async function Layout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode
  params: Promise<{ id: string }>
}>) {
  const { id } = await params
  return (
    <>
      <Suspense fallback={null}>
        <ChatShell initialSessionId={id} />
      </Suspense>
      {children}
    </>
  )
}
