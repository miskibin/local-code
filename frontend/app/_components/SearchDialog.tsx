"use client";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import type { Session } from "@/lib/types";

export function SearchDialog({
  open,
  onOpenChange,
  sessions,
  onSelect,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  sessions: Session[];
  onSelect: (id: string) => void;
}) {
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search chats..." />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>
        <CommandGroup heading="Chats">
          {sessions.map((s) => (
            <CommandItem
              key={s.id}
              value={`${s.title} ${s.id}`}
              onSelect={() => {
                onSelect(s.id);
                onOpenChange(false);
              }}
            >
              {s.title || "Untitled"}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
