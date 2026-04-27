"use client"

import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DraggableAttributes,
  type DraggableSyntheticListeners,
} from "@dnd-kit/core"
import {
  ChevronRight,
  Cpu,
  Database,
  ListChecks,
  MoreHorizontal,
  PanelLeft,
  Pencil,
  Pin,
  PinOff,
  Search,
  Settings,
  Trash2,
} from "lucide-react"
import Link from "next/link"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Artifact, Session } from "@/lib/types"

type Props = {
  collapsed: boolean
  onToggle: () => void
  sessions: Session[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onSearch: () => void
  onDeleteSession: (id: string) => void
  onTrashSession: (id: string) => void
  onRenameSession: (id: string, title: string) => void
  onTogglePinSession: (id: string, pinned: boolean) => void
  artifacts: Artifact[]
  onOpenArtifact: (a: Artifact) => void
  onDeleteArtifact: (id: string) => void
  onTrashArtifact: (id: string) => void
}

export function Sidebar({
  collapsed,
  onToggle,
  sessions,
  activeId,
  onSelect,
  onNew,
  onSearch,
  onDeleteSession,
  onTrashSession,
  onRenameSession,
  onTogglePinSession,
  artifacts,
  onOpenArtifact,
  onDeleteArtifact,
  onTrashArtifact,
}: Props) {
  const [chatsOpen, setChatsOpen] = useState(true)
  const [artifactsOpen, setArtifactsOpen] = useState(true)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor)
  )
  const [activeDragId, setActiveDragId] = useState<string | null>(null)
  const draggedSession = useMemo(
    () => sessions.find((s) => s.id === activeDragId) ?? null,
    [sessions, activeDragId]
  )
  const handleDragStart = (e: DragStartEvent) =>
    setActiveDragId(String(e.active.id))
  const handleDragCancel = () => setActiveDragId(null)
  const handleDragEnd = (e: DragEndEvent) => {
    const id = String(e.active.id)
    const overId = e.over?.id ? String(e.over.id) : null
    setActiveDragId(null)
    if (!overId) return
    const s = sessions.find((x) => x.id === id)
    if (!s) return
    if (overId === "pin-zone") {
      if (!s.is_pinned) onTogglePinSession(id, true)
    } else if (overId === "trash-zone") {
      onTrashSession(id)
    }
  }

  const [activeArtifactDragId, setActiveArtifactDragId] = useState<
    string | null
  >(null)
  const draggedArtifact = useMemo(
    () => artifacts.find((a) => a.id === activeArtifactDragId) ?? null,
    [artifacts, activeArtifactDragId]
  )
  const handleArtifactDragStart = (e: DragStartEvent) =>
    setActiveArtifactDragId(String(e.active.id))
  const handleArtifactDragCancel = () => setActiveArtifactDragId(null)
  const handleArtifactDragEnd = (e: DragEndEvent) => {
    const id = String(e.active.id)
    const overId = e.over?.id ? String(e.over.id) : null
    setActiveArtifactDragId(null)
    if (overId === "artifact-trash-zone") onTrashArtifact(id)
  }

  if (collapsed) {
    return (
      <div
        className="lc-sidebar-wrap flex flex-shrink-0 flex-col items-center gap-1.5 py-3"
        style={{
          width: 56,
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border)",
        }}
      >
        <SideIconBtn label="Open sidebar" onClick={onToggle}>
          <PanelLeft className="h-4 w-4" />
        </SideIconBtn>
        <SideIconBtn label="New chat" onClick={onNew}>
          <Pencil className="h-4 w-4" />
        </SideIconBtn>
        <SideIconBtn label="Search" onClick={onSearch}>
          <Search className="h-4 w-4" />
        </SideIconBtn>
        <Link href="/tasks" aria-label="Tasks">
          <SideIconBtn label="Tasks">
            <ListChecks className="h-4 w-4" />
          </SideIconBtn>
        </Link>
        <div className="flex-1" />
        <Link href="/settings" aria-label="Settings">
          <SideIconBtn label="Settings">
            <Settings className="h-4 w-4" />
          </SideIconBtn>
        </Link>
      </div>
    )
  }

  return (
    <div
      className="lc-sidebar-wrap flex min-w-0 flex-shrink-0 flex-col"
      style={{
        width: 260,
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border)",
      }}
    >
      <div className="flex items-center justify-end px-2.5 pt-2.5 pb-1.5">
        <button
          onClick={onToggle}
          title="Collapse sidebar"
          className="inline-flex items-center justify-center rounded-md p-1.5"
          style={{
            background: "transparent",
            border: 0,
            color: "var(--ink-2)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--hover)"
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent"
          }}
        >
          <PanelLeft className="h-[17px] w-[17px]" />
        </button>
      </div>

      <div className="px-2 pb-0.5">
        <SideRow icon={<Pencil className="h-4 w-4" />} onClick={onNew}>
          New chat
        </SideRow>
        <SideRow icon={<Search className="h-4 w-4" />} onClick={onSearch}>
          Search chats
        </SideRow>
        <Link href="/tasks" className="block">
          <SideRow icon={<ListChecks className="h-4 w-4" />}>Tasks</SideRow>
        </Link>
      </div>

      <div className="lc-scroll flex-1 overflow-y-auto px-2 pt-3 pb-2">
        <SectionHead
          open={chatsOpen}
          onToggle={() => setChatsOpen((o) => !o)}
          count={sessions.length}
        >
          Chats
        </SectionHead>
        {chatsOpen && (
          <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
          >
            <DropZone
              id="pin-zone"
              icon={<Pin className="h-3.5 w-3.5" />}
              label="Drop here to pin"
              tone="accent"
              visible={activeDragId !== null}
            />
            {sessions.map((s, i) => {
              const listNumber = s.is_pinned
                ? undefined
                : sessions.slice(0, i).filter((x) => !x.is_pinned).length + 1
              return (
                <DraggableChatRow
                  key={s.id}
                  listNumber={listNumber}
                  session={s}
                  active={s.id === activeId}
                  isBeingDragged={activeDragId === s.id}
                  onSelect={() => onSelect(s.id)}
                  onDelete={() => onDeleteSession(s.id)}
                  onRename={(title) => onRenameSession(s.id, title)}
                  onTogglePin={() => onTogglePinSession(s.id, !s.is_pinned)}
                />
              )
            })}
            <DropZone
              id="trash-zone"
              icon={<Trash2 className="h-3.5 w-3.5" />}
              label="Drop here to delete"
              tone="danger"
              visible={activeDragId !== null}
            />
            <DragOverlay dropAnimation={null}>
              {draggedSession ? <ChatRowGhost session={draggedSession} /> : null}
            </DragOverlay>
          </DndContext>
        )}

        <div className="h-3.5" />

        <SectionHead
          open={artifactsOpen}
          onToggle={() => setArtifactsOpen((o) => !o)}
          count={artifacts.length}
        >
          Artifacts
        </SectionHead>
        {artifactsOpen &&
          (artifacts.length === 0 ? (
            <div
              className="px-2.5 py-2"
              style={{ fontSize: 12, color: "var(--ink-3)" }}
            >
              Saved tables and charts appear here.
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              onDragStart={handleArtifactDragStart}
              onDragEnd={handleArtifactDragEnd}
              onDragCancel={handleArtifactDragCancel}
            >
              {artifacts.map((a) => (
                <DraggableArtifactRow
                  key={a.id}
                  artifact={a}
                  isBeingDragged={activeArtifactDragId === a.id}
                  onOpen={() => onOpenArtifact(a)}
                  onDelete={() => onDeleteArtifact(a.id)}
                />
              ))}
              <DropZone
                id="artifact-trash-zone"
                icon={<Trash2 className="h-3.5 w-3.5" />}
                label="Drop here to delete"
                tone="danger"
                visible={activeArtifactDragId !== null}
              />
              <DragOverlay dropAnimation={null}>
                {draggedArtifact ? (
                  <ArtifactRowGhost artifact={draggedArtifact} />
                ) : null}
              </DragOverlay>
            </DndContext>
          ))}
      </div>

      <div className="p-2" style={{ borderTop: "1px solid var(--border)" }}>
        <Link href="/settings" className="block">
          <SideRow icon={<Settings className="h-4 w-4" />}>Settings</SideRow>
        </Link>
      </div>
    </div>
  )
}

type ArtifactRowProps = {
  artifact: Artifact
  onOpen: () => void
  onDelete: () => void
  dragAttrs?: DraggableAttributes
  dragListeners?: DraggableSyntheticListeners
  dragNodeRef?: (el: HTMLDivElement | null) => void
  isBeingDragged?: boolean
}

function ArtifactRow({
  artifact,
  onOpen,
  onDelete,
  dragAttrs,
  dragListeners,
  dragNodeRef,
  isBeingDragged,
}: ArtifactRowProps) {
  return (
    <div
      ref={dragNodeRef}
      {...(dragAttrs ?? {})}
      {...(dragListeners ?? {})}
      className="group/row relative"
      style={{
        opacity: isBeingDragged ? 0.4 : 1,
        touchAction: dragListeners ? "none" : undefined,
      }}
    >
      <button
        onClick={onOpen}
        title={artifact.title}
        className="mb-px flex w-full items-center gap-2 truncate rounded-md py-1.5 pr-9 pl-2.5 text-left"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink)",
          fontSize: 13,
          cursor: dragListeners ? "grab" : "pointer",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--hover)"
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent"
        }}
      >
        <span
          className="inline-flex flex-shrink-0"
          style={{ color: "var(--accent)" }}
        >
          {artifact.kind === "table" ? (
            <Database className="h-3 w-3" />
          ) : (
            <Cpu className="h-3 w-3" />
          )}
        </span>
        <span className="flex-1 truncate">{artifact.title}</span>
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        onPointerDown={(e) => e.stopPropagation()}
        title="Delete"
        className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md p-1 opacity-0 transition group-hover/row:opacity-100"
        style={{
          background: "transparent",
          border: 0,
          color: "var(--ink-3)",
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function DraggableArtifactRow(
  props: Omit<
    ArtifactRowProps,
    "dragAttrs" | "dragListeners" | "dragNodeRef"
  > & { isBeingDragged: boolean }
) {
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: props.artifact.id,
  })
  return (
    <ArtifactRow
      {...props}
      dragAttrs={attributes}
      dragListeners={listeners}
      dragNodeRef={setNodeRef}
    />
  )
}

function ArtifactRowGhost({ artifact }: { artifact: Artifact }) {
  return (
    <div
      className="flex items-center gap-2 truncate rounded-md py-1.5 pr-3 pl-2.5"
      style={{
        background: "var(--bg-sidebar)",
        color: "var(--ink)",
        border: "1px solid var(--accent)",
        boxShadow: "0 8px 18px -8px rgba(0,0,0,.35)",
        fontSize: 13,
        width: 240,
        cursor: "grabbing",
      }}
    >
      <span
        className="inline-flex flex-shrink-0"
        style={{ color: "var(--accent)" }}
      >
        {artifact.kind === "table" ? (
          <Database className="h-3 w-3" />
        ) : (
          <Cpu className="h-3 w-3" />
        )}
      </span>
      <span className="flex-1 truncate">{artifact.title}</span>
    </div>
  )
}

type ChatRowProps = {
  session: Session
  /** 1-based index among unpinned chats only; omitted when pinned */
  listNumber?: number
  active: boolean
  editing: boolean
  setEditing: (v: boolean) => void
  onSelect: () => void
  onDelete: () => void
  onRename: (title: string) => void
  onTogglePin: () => void
  dragAttrs?: DraggableAttributes
  dragListeners?: DraggableSyntheticListeners
  dragNodeRef?: (el: HTMLDivElement | null) => void
  isBeingDragged?: boolean
}

function ChatRow({
  session,
  listNumber,
  active,
  editing,
  setEditing,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
  dragAttrs,
  dragListeners,
  dragNodeRef,
  isBeingDragged,
}: ChatRowProps) {
  const [draft, setDraft] = useState(session.title || "")
  const inputRef = useRef<HTMLInputElement>(null)
  const isPinned = !!session.is_pinned

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  const startEdit = () => {
    setDraft(session.title || "")
    setEditing(true)
  }

  const commit = () => {
    setEditing(false)
    const next = draft.trim()
    if (next && next !== (session.title || "")) onRename(next)
  }

  const cancel = () => {
    setEditing(false)
    setDraft(session.title || "")
  }

  return (
    <div
      ref={dragNodeRef}
      {...(dragAttrs ?? {})}
      {...(!editing && dragListeners ? dragListeners : {})}
      className="group/row relative"
      style={{
        opacity: isBeingDragged ? 0.4 : 1,
        touchAction: dragListeners ? "none" : undefined,
      }}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              commit()
            } else if (e.key === "Escape") {
              e.preventDefault()
              cancel()
            }
          }}
          className="mb-px block w-full truncate py-1.5 pr-9 pl-2.5 text-left outline-none"
          style={{
            background: "var(--hover)",
            color: "var(--ink)",
            border: 0,
            borderLeft: "2px solid var(--accent)",
            fontSize: 13.5,
          }}
        />
      ) : (
        <button
          onClick={onSelect}
          onDoubleClick={startEdit}
          title={session.title || "Untitled"}
          className="mb-px flex w-full items-center gap-1.5 truncate py-1.5 pr-9 pl-2.5 text-left"
          style={{
            background: "transparent",
            color: "var(--ink)",
            border: 0,
            borderLeft: active
              ? "2px solid var(--accent)"
              : "2px solid transparent",
            fontSize: 13.5,
            fontWeight: active ? 500 : 400,
            cursor: dragListeners ? "grab" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (!active) e.currentTarget.style.background = "var(--hover)"
          }}
          onMouseLeave={(e) => {
            if (!active) e.currentTarget.style.background = "transparent"
          }}
        >
          {isPinned && (
            <Pin
              className="h-3 w-3 flex-shrink-0"
              style={{ color: "var(--accent)" }}
            />
          )}
          {listNumber != null && (
            <span
              className="flex-shrink-0 tabular-nums"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: active ? "var(--accent)" : "var(--ink-4)",
              }}
            >
              {String(listNumber).padStart(2, "0")}
            </span>
          )}
          <span className="flex-1 truncate">
            {session.title || "Untitled"}
          </span>
        </button>
      )}
      {!editing && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              onClick={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              title="More"
              className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md p-1 opacity-0 transition group-hover/row:opacity-100 data-[state=open]:opacity-100"
              style={{
                background: "transparent",
                border: 0,
                color: "var(--ink-3)",
              }}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onSelect={() => startEdit()}>
              <Pencil className="h-3.5 w-3.5" />
              <span>Rename</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onTogglePin()}>
              {isPinned ? (
                <>
                  <PinOff className="h-3.5 w-3.5" />
                  <span>Unpin</span>
                </>
              ) : (
                <>
                  <Pin className="h-3.5 w-3.5" />
                  <span>Pin</span>
                </>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => onDelete()}
              variant="destructive"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Delete</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  )
}

function DraggableChatRow(
  props: Omit<
    ChatRowProps,
    "dragAttrs" | "dragListeners" | "dragNodeRef" | "editing" | "setEditing"
  > & { isBeingDragged: boolean }
) {
  const [editing, setEditing] = useState(false)
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: props.session.id,
    disabled: editing,
  })
  return (
    <ChatRow
      {...props}
      editing={editing}
      setEditing={setEditing}
      dragAttrs={attributes}
      dragListeners={listeners}
      dragNodeRef={setNodeRef}
    />
  )
}

function ChatRowGhost({ session }: { session: Session }) {
  const isPinned = !!session.is_pinned
  return (
    <div
      className="flex items-center gap-1.5 truncate rounded-md py-1.5 pr-3 pl-2.5"
      style={{
        background: "var(--bg-sidebar)",
        color: "var(--ink)",
        border: "1px solid var(--accent)",
        boxShadow: "0 8px 18px -8px rgba(0,0,0,.35)",
        fontSize: 13.5,
        width: 240,
        cursor: "grabbing",
      }}
    >
      {isPinned && (
        <Pin
          className="h-3 w-3 flex-shrink-0"
          style={{ color: "var(--accent)" }}
        />
      )}
      <span className="flex-1 truncate">{session.title || "Untitled"}</span>
    </div>
  )
}

function DropZone({
  id,
  icon,
  label,
  tone,
  visible,
}: {
  id: string
  icon: React.ReactNode
  label: string
  tone: "accent" | "danger"
  visible: boolean
}) {
  const { setNodeRef, isOver } = useDroppable({ id })
  const color = tone === "danger" ? "var(--destructive)" : "var(--accent)"
  return (
    <div
      ref={setNodeRef}
      aria-hidden={!visible}
      className="overflow-hidden"
      style={{
        maxHeight: visible ? 38 : 0,
        marginTop: visible ? 4 : 0,
        marginBottom: visible ? 4 : 0,
        opacity: visible ? 1 : 0,
        transition:
          "max-height 160ms ease, opacity 160ms ease, margin 160ms ease",
        pointerEvents: visible ? "auto" : "none",
      }}
    >
      <div
        className="mx-1 flex items-center justify-center gap-1.5 rounded-md py-1.5"
        style={{
          fontSize: 12,
          fontWeight: 500,
          color: isOver ? "var(--accent-foreground, #fff)" : color,
          background: isOver ? color : "transparent",
          border: `1px dashed ${color}`,
          transition: "background 120ms ease, color 120ms ease",
        }}
      >
        {icon}
        <span>{label}</span>
      </div>
    </div>
  )
}

function SectionHead({
  open,
  onToggle,
  count,
  children,
}: {
  open: boolean
  onToggle: () => void
  count: number
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center gap-1.5 px-2.5 pt-1 pb-1 uppercase"
      style={{
        background: "transparent",
        border: 0,
        color: "var(--ink-3)",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: ".04em",
      }}
    >
      <span
        className="inline-flex transition-transform"
        style={{ transform: open ? "rotate(90deg)" : "none" }}
      >
        <ChevronRight className="h-3 w-3" />
      </span>
      <span>{children}</span>
      <span
        className="ml-auto"
        style={{ color: "var(--ink-4)", fontWeight: 400 }}
      >
        {count}
      </span>
    </button>
  )
}

function SideRow({
  icon,
  children,
  onClick,
}: {
  icon: React.ReactNode
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13.5px]"
      style={{
        background: "transparent",
        border: 0,
        color: "var(--ink)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      <span className="inline-flex" style={{ color: "var(--ink-2)" }}>
        {icon}
      </span>
      <span>{children}</span>
    </button>
  )
}

function SideIconBtn({
  label,
  onClick,
  children,
}: {
  label: string
  onClick?: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      className="rounded-md p-2"
      style={{ background: "transparent", border: 0, color: "var(--ink-2)" }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--hover)"
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent"
      }}
    >
      {children}
    </button>
  )
}
