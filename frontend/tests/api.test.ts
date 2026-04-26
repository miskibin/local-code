import { describe, it, expect, beforeEach, vi } from "vitest";
import { api } from "@/lib/api";

describe("api wrappers", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("listArtifacts GETs /artifacts and returns parsed JSON", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: "a1", kind: "table", title: "t", payload: {} }]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const out = await api.listArtifacts();
    expect(out[0].id).toBe("a1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url.endsWith("/artifacts")).toBe(true);
  });

  it("saveArtifact POSTs JSON body", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "a2", kind: "chart", title: "x", payload: {} }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    await api.saveArtifact({ id: "a2", kind: "chart", title: "x", payload: { data: [] } });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toContain('"id":"a2"');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("throws on non-2xx", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response("nope", { status: 500 }));
    await expect(api.listSessions()).rejects.toThrow();
  });
});
