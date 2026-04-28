export type TaskRoleId =
  | "local_product_owner"
  | "fot_leader"
  | "area_product_owner"
  | "product_manager"

export type TaskRole = {
  id: TaskRoleId
  label: string
  short: string
  color: string
  soft: string
}

export const TASK_ROLES: TaskRole[] = [
  {
    id: "local_product_owner",
    label: "Local Product Owner",
    short: "Local Product Owner",
    color: "#1d4ed8",
    soft: "#eff4ff",
  },
  {
    id: "fot_leader",
    label: "FOT Leader",
    short: "FOT Leader",
    color: "#b45309",
    soft: "#fffbeb",
  },
  {
    id: "area_product_owner",
    label: "Area Product Owner",
    short: "Area Product Owner",
    color: "#7e22ce",
    soft: "#faf5ff",
  },
  {
    id: "product_manager",
    label: "Product Manager",
    short: "Product Manager",
    color: "#0e7490",
    soft: "#ecfeff",
  },
]

const ROLE_BY_ID = new Map<string, TaskRole>(TASK_ROLES.map((r) => [r.id, r]))

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
