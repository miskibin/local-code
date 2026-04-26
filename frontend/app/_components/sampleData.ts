import type { Artifact, AssistantStep } from "@/lib/types";

export const DEMO_SUBAGENT_STEPS: AssistantStep[] = [
  {
    kind: "subagent",
    agent: { id: "sql-analyst", name: "SQL Analyst" },
    task: "Pull Q1 sales totals grouped by region from the warehouse.",
    duration: "2.4s",
    status: "done",
    steps: [
      {
        kind: "tool",
        tool: "sqlite_list_tables",
        server: "sqlite",
        args: {},
        result: "4 tables · sales, customers, regions, products",
        duration: "0.05s",
      },
      {
        kind: "tool",
        tool: "sqlite_schema",
        server: "sqlite",
        args: { table: "sales" },
        result: "columns: id, customer_id, region, amount, date",
        duration: "0.04s",
      },
      {
        kind: "tool",
        tool: "sqlite_query",
        server: "sqlite",
        args: {
          sql: "SELECT region, SUM(amount) AS revenue, COUNT(*) AS orders FROM sales WHERE date >= '2026-01-01' AND date < '2026-04-01' GROUP BY region ORDER BY revenue DESC",
        },
        result: "4 rows returned",
        duration: "0.09s",
      },
    ],
    artifact: {
      id: "sa-q1-region-table",
      kind: "table",
      title: "Q1 2026 sales by region",
      payload: {
        columns: [
          { key: "region", label: "Region" },
          { key: "orders", label: "Orders", numeric: true },
          { key: "revenue", label: "Revenue", numeric: true, format: "currency" },
          { key: "avg", label: "Avg order", numeric: true, format: "currency" },
        ],
        rows: [
          { region: "NA", orders: 1842, revenue: 412300, avg: 224 },
          { region: "EMEA", orders: 1207, revenue: 298100, avg: 247 },
          { region: "APAC", orders: 684, revenue: 152400, avg: 223 },
          { region: "LATAM", orders: 329, revenue: 71800, avg: 218 },
        ],
      },
    },
    summary:
      "NA leads at $412K (44% of revenue), but EMEA has the highest average order value at $247.",
  },
];

// 1x1 transparent PNG used as a sample image artifact.
const TRANSPARENT_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

export const DEMO_SAMPLE_ARTIFACT: Artifact = {
  id: "demo-sample-image",
  kind: "image",
  title: "Revenue by customer (top 10)",
  payload: {
    format: "png",
    data_b64: TRANSPARENT_PNG_B64,
    caption: "Q1 2026 · USD",
  },
};
