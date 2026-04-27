import { redirect } from "next/navigation"
import { nanoid } from "nanoid"

export default function Page() {
  redirect(`/chat/${nanoid()}`)
}
