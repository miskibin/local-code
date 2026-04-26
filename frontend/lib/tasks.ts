import type { useRouter } from "next/navigation";

type Router = ReturnType<typeof useRouter>;

export function encodeTaskRun(
  taskId: string,
  variables: Record<string, unknown>,
): string {
  return btoa(
    encodeURIComponent(JSON.stringify({ task_id: taskId, variables })),
  );
}

export function decodeTaskRun(
  token: string | null,
): { task_id: string; variables: Record<string, unknown> } | null {
  if (!token) return null;
  try {
    const decoded = JSON.parse(decodeURIComponent(atob(token)));
    if (typeof decoded?.task_id !== "string") return null;
    const vars =
      decoded.variables && typeof decoded.variables === "object"
        ? (decoded.variables as Record<string, unknown>)
        : {};
    return { task_id: decoded.task_id, variables: vars };
  } catch {
    return null;
  }
}

export function navigateToTaskRunUrl(
  router: Router,
  taskId: string,
  variables: Record<string, unknown>,
): void {
  router.push(`/?taskRun=${encodeTaskRun(taskId, variables)}`);
}
