import { expect, test } from "@playwright/test";

const BACKEND = process.env.E2E_BACKEND_URL ?? "http://localhost:8000";

test("GET /artifacts/{id} returns full DTO with source_code; refresh bumps payload", async ({
  request,
}) => {
  const id = "e2e-api-1";
  // start fresh
  await request.delete(`${BACKEND}/artifacts/${id}`).catch(() => undefined);

  // create with python source that emits a deterministic table
  const create = await request.post(`${BACKEND}/artifacts`, {
    data: {
      id,
      kind: "table",
      title: "stale",
      payload: { columns: [], rows: [] },
      summary: "",
      source_kind: "python",
      source_code: "out([{'n': 11}])",
    },
  });
  expect(create.ok(), await create.text()).toBeTruthy();

  // GET returns source_code (proves it's stored, not just streamed)
  const got = await request.get(`${BACKEND}/artifacts/${id}`);
  expect(got.status()).toBe(200);
  const body = await got.json();
  expect(body.source_code).toBe("out([{'n': 11}])");
  expect(body.source_kind).toBe("python");

  // refresh re-executes
  const refreshed = await request.post(`${BACKEND}/artifacts/${id}/refresh`);
  expect(refreshed.ok(), await refreshed.text()).toBeTruthy();
  const fresh = await refreshed.json();
  expect(fresh.payload.rows).toEqual([{ n: 11 }]);
  expect(new Date(fresh.updated_at).getTime()).toBeGreaterThanOrEqual(
    new Date(body.updated_at).getTime(),
  );

  await request.delete(`${BACKEND}/artifacts/${id}`);
});

test("refresh fails clearly when artifact has no source", async ({ request }) => {
  const id = "e2e-no-source";
  await request.delete(`${BACKEND}/artifacts/${id}`).catch(() => undefined);
  await request.post(`${BACKEND}/artifacts`, {
    data: {
      id,
      kind: "text",
      title: "manual",
      payload: { text: "x" },
      summary: "x",
    },
  });

  const r = await request.post(`${BACKEND}/artifacts/${id}/refresh`);
  expect(r.status()).toBe(400);

  await request.delete(`${BACKEND}/artifacts/${id}`);
});
