import { Suspense } from "react";
import { ChatShell } from "./_components/ChatShell";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ChatShell />
    </Suspense>
  );
}
