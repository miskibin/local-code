import { toast } from "sonner"

export type UndoableEntry<T> = { undone: boolean; item: T; index: number }

export type UndoableDeleteOpts<T> = {
  id: string
  items: T[]
  pending: Map<string, UndoableEntry<T>>
  setItems: (updater: (prev: T[]) => T[]) => void
  getId: (item: T) => string
  toastTitle: (item: T) => string
  errorTitle: string
  errorLogTag: string
  confirm: (id: string) => Promise<unknown>
  refresh: () => void
  beforeShow?: (item: T) => void
}

export function showUndoableDelete<T>(opts: UndoableDeleteOpts<T>): void {
  const {
    id,
    items,
    pending,
    setItems,
    getId,
    toastTitle,
    errorTitle,
    errorLogTag,
    confirm,
    refresh,
    beforeShow,
  } = opts
  const idx = items.findIndex((it) => getId(it) === id)
  if (idx < 0) return
  const item = items[idx]
  pending.set(id, { undone: false, item, index: idx })
  setItems((prev) => prev.filter((it) => getId(it) !== id))
  beforeShow?.(item)
  toast(toastTitle(item), {
    duration: 5000,
    action: {
      label: "Undo",
      onClick: () => {
        const entry = pending.get(id)
        if (!entry) return
        entry.undone = true
        pending.delete(id)
        setItems((prev) => {
          if (prev.some((it) => getId(it) === id)) return prev
          const next = [...prev]
          next.splice(Math.min(entry.index, next.length), 0, entry.item)
          return next
        })
      },
    },
    onAutoClose: () => {
      const entry = pending.get(id)
      if (!entry || entry.undone) return
      pending.delete(id)
      confirm(id).catch((e) => {
        console.error(errorLogTag, e)
        toast.error(errorTitle, { description: String(e) })
        refresh()
      })
    },
  })
}
