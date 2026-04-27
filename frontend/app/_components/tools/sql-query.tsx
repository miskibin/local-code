"use client"

import type { ToolRenderer } from "./types"

const ZERO_ROWS = /\b0\s+rows?\b/i

function isEmptyResult(result: string): boolean {
  if (!result) return false
  // sql_query result format: "art_xxx · sql N rows x M cols (...)".
  // Match "0 rows" / "0 row" anywhere in the summary.
  return ZERO_ROWS.test(result)
}

export const sqlQueryRenderer: ToolRenderer = {
  getStatusOverride: (step) => {
    if (step.status !== "done") return null
    return isEmptyResult(step.result) ? "warning" : null
  },
}
