"use client"

import { useMemo, useState } from "react"
import { Code2, FormInput } from "lucide-react"
import type { JSONSchema } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type Args = Record<string, unknown>

const fieldChrome =
  "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink)] shadow-[inset_0_1px_0_color-mix(in_oklab,var(--ink)_4%,transparent)]"

type Props = {
  schema: JSONSchema | null | undefined
  value: Args | null | undefined
  onChange: (value: Args) => void
}

function isTemplateString(v: unknown): boolean {
  return typeof v === "string" && v.includes("{{")
}

function fieldType(s: JSONSchema): string {
  if (typeof s.$ref === "string") return "object"
  if (Array.isArray(s.type)) {
    return s.type.find((t) => t !== "null") ?? "string"
  }
  if (typeof s.type === "string") return s.type
  if (s.properties) return "object"
  if (s.items) return "array"
  if (Array.isArray(s.anyOf)) {
    const inner = s.anyOf.find(
      (a): a is JSONSchema =>
        typeof a === "object" && a !== null && (a as JSONSchema).type !== "null"
    )
    if (inner) return fieldType(inner)
  }
  if (Array.isArray(s.oneOf) || Array.isArray(s.allOf)) return "object"
  return "string"
}

function FieldRow({
  name,
  schema,
  value,
  required,
  onChange,
}: {
  name: string
  schema: JSONSchema
  value: unknown
  required: boolean
  onChange: (v: unknown) => void
}) {
  const t = fieldType(schema)
  const enumValues = schema.enum as (string | number)[] | undefined
  const description = schema.description
  const title = schema.title || name

  let control: React.ReactNode

  if (enumValues && enumValues.length > 0) {
    control = (
      <Select value={String(value ?? "")} onValueChange={(v) => onChange(v)}>
        <SelectTrigger className={cn("w-full", fieldChrome)}>
          <SelectValue placeholder="Choose…" />
        </SelectTrigger>
        <SelectContent>
          {enumValues.map((opt) => (
            <SelectItem key={String(opt)} value={String(opt)}>
              {String(opt)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  } else if (t === "boolean") {
    control = (
      <Switch checked={Boolean(value)} onCheckedChange={(c) => onChange(c)} />
    )
  } else if (t === "integer" || t === "number") {
    control = (
      <Input
        className={fieldChrome}
        inputMode="numeric"
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) => {
          const raw = e.target.value
          if (raw === "") {
            onChange(undefined)
            return
          }
          if (raw.includes("{{")) {
            onChange(raw)
            return
          }
          const num = t === "integer" ? parseInt(raw, 10) : parseFloat(raw)
          onChange(Number.isNaN(num) ? raw : num)
        }}
        placeholder={description}
      />
    )
  } else if (t === "string") {
    const strVal =
      typeof value === "string"
        ? value
        : value === undefined || value === null
          ? ""
          : typeof value === "number" || typeof value === "boolean"
            ? String(value)
            : JSON.stringify(value, null, 2)
    const codeLike =
      /^(code|query|sql|script|python|body|payload)$/i.test(name) ||
      (description?.toLowerCase().includes("sql") ?? false)
    control = (
      <Textarea
        value={strVal}
        onChange={(e) => onChange(e.target.value)}
        placeholder={description}
        rows={codeLike ? 10 : 6}
        className={cn(
          fieldChrome,
          codeLike ? "min-h-[10.5rem] font-mono text-xs" : "min-h-[7.5rem]"
        )}
      />
    )
  } else {
    const text = (() => {
      if (isTemplateString(value)) return value as string
      try {
        return JSON.stringify(value ?? null, null, 2)
      } catch {
        return ""
      }
    })()
    control = (
      <Textarea
        value={text}
        onChange={(e) => {
          const raw = e.target.value
          if (raw.includes("{{")) {
            onChange(raw)
            return
          }
          try {
            onChange(JSON.parse(raw || "null"))
          } catch {
            onChange(raw)
          }
        }}
        rows={4}
        className={cn(fieldChrome, "font-mono text-xs")}
      />
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <Label className="text-xs text-[var(--ink-2)]">
        <span className="font-semibold text-[var(--ink)]">{title}</span>
        {required && <span style={{ color: "var(--accent)" }}> *</span>}
        <span className="ml-1 font-mono text-[10px] text-[var(--ink-2)]">
          {t}
        </span>
      </Label>
      {control}
      {description && (
        <span className="text-[12px] leading-snug text-[var(--ink-2)]">
          {description}
        </span>
      )}
    </div>
  )
}

export function SchemaArgsEditor({ schema, value, onChange }: Props) {
  const [mode, setMode] = useState<"form" | "json">("form")
  const properties = schema?.properties ?? {}
  const required = useMemo(() => new Set(schema?.required ?? []), [schema])
  const propEntries = Object.entries(properties)

  const args = useMemo<Args>(() => value ?? {}, [value])

  const updateField = (key: string, v: unknown) => {
    const next = { ...args }
    if (v === undefined) delete next[key]
    else next[key] = v
    onChange(next)
  }

  const jsonText = useMemo(() => {
    try {
      return JSON.stringify(args, null, 2)
    } catch {
      return "{}"
    }
  }, [args])

  const showForm = mode === "form" && propEntries.length > 0

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <Label className="text-xs font-semibold tracking-wider text-[var(--ink-2)] uppercase">
          Arguments
        </Label>
        {propEntries.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => setMode(mode === "form" ? "json" : "form")}
            className="h-6 gap-1 text-[11px]"
          >
            {mode === "form" ? (
              <>
                <Code2 className="h-3 w-3" /> JSON
              </>
            ) : (
              <>
                <FormInput className="h-3 w-3" /> Form
              </>
            )}
          </Button>
        )}
      </div>
      {showForm ? (
        <div className="flex flex-col gap-3">
          {propEntries.map(([key, sub]) => (
            <FieldRow
              key={key}
              name={key}
              schema={sub}
              value={args[key]}
              required={required.has(key)}
              onChange={(v) => updateField(key, v)}
            />
          ))}
        </div>
      ) : (
        <Textarea
          value={jsonText}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value || "{}")
              if (
                parsed &&
                typeof parsed === "object" &&
                !Array.isArray(parsed)
              ) {
                onChange(parsed as Args)
              }
            } catch {
              /* user mid-edit */
            }
          }}
          rows={Math.max(6, Math.min(jsonText.split("\n").length + 1, 16))}
          className={cn(fieldChrome, "font-mono text-xs")}
        />
      )}
      {propEntries.length === 0 && schema && (
        <div className="text-xs text-[var(--ink-2)]">
          Tool takes no arguments.
        </div>
      )}
    </div>
  )
}
