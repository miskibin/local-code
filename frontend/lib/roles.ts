export type TaskRole = {
  id: string
  label: string
  short: string
  color: string
  soft: string
}

export const TASK_ROLES: TaskRole[] = [
  { id: "local-po", label: "Local Product Owner", short: "Local PO", color: "#1d4ed8", soft: "#eff4ff" },
  { id: "apo", label: "Area Product Owner", short: "APO", color: "#7e22ce", soft: "#faf5ff" },
  { id: "pm", label: "Product Manager", short: "PM", color: "#0e7490", soft: "#ecfeff" },
  { id: "engineer", label: "Engineer", short: "Eng", color: "#047857", soft: "#ecfdf5" },
  { id: "designer", label: "Designer", short: "Design", color: "#be185d", soft: "#fdf2f8" },
  { id: "analyst", label: "Data Analyst", short: "Analyst", color: "#b45309", soft: "#fffbeb" },
  { id: "researcher", label: "UX Researcher", short: "Research", color: "#4338ca", soft: "#eef2ff" },
  { id: "ops", label: "Operations", short: "Ops", color: "#475569", soft: "#f1f5f9" },
]

const ROLE_BY_ID = new Map(TASK_ROLES.map((r) => [r.id, r]))

export function getRole(id: string | null | undefined): TaskRole | undefined {
  return id ? ROLE_BY_ID.get(id) : undefined
}

export function hexAlpha(hex: string, a: number): string {
  const h = hex.replace("#", "")
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}
