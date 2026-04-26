import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ArtifactModal } from "@/app/_components/ArtifactModal";
import type { Artifact } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: { refreshArtifact: vi.fn() },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { api } from "@/lib/api";
import { toast } from "sonner";

const baseArtifact: Artifact = {
  id: "art-1",
  kind: "table",
  title: "Demo table",
  payload: {
    columns: [{ key: "n", label: "n" }],
    rows: [{ n: 7 }],
  },
  summary: "table 1 rows × 1 cols (n)",
  source_kind: "python",
  source_code: "out([{'n': 7}])",
  updated_at: new Date(Date.now() - 60_000).toISOString(),
};

describe("ArtifactModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses wide sizing classes (overrides shadcn sm:max-w-sm clamp)", () => {
    render(<ArtifactModal artifact={baseArtifact} onClose={vi.fn()} />);
    const dialog = document.querySelector("[data-slot='dialog-content']")!;
    expect(dialog.className).toContain("w-[95vw]");
    expect(dialog.className).toContain("sm:max-w-[1400px]");
    expect(dialog.className).not.toContain("max-w-[880px]");
  });

  it("shows updated-ago pill and a collapsed source-code section", () => {
    render(<ArtifactModal artifact={baseArtifact} onClose={vi.fn()} />);
    expect(screen.getByText(/Updated/i)).toBeInTheDocument();
    const details = document.querySelector("details");
    expect(details).not.toBeNull();
    expect(details?.open).toBe(false);
    expect(screen.getByText(/Source code/i)).toBeInTheDocument();
  });

  it("calls refreshArtifact and onRefreshed when Refresh clicked", async () => {
    const fresh: Artifact = {
      ...baseArtifact,
      payload: { ...baseArtifact.payload, rows: [{ n: 99 }] },
      updated_at: new Date().toISOString(),
    };
    (api.refreshArtifact as ReturnType<typeof vi.fn>).mockResolvedValue(fresh);
    const onRefreshed = vi.fn();
    render(
      <ArtifactModal
        artifact={baseArtifact}
        onClose={vi.fn()}
        onRefreshed={onRefreshed}
      />,
    );
    await userEvent.click(screen.getByTestId("artifact-refresh"));
    await waitFor(() => {
      expect(api.refreshArtifact).toHaveBeenCalledWith("art-1");
      expect(onRefreshed).toHaveBeenCalledWith(fresh);
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it("toasts on refresh failure and does not call onRefreshed", async () => {
    (api.refreshArtifact as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("boom"),
    );
    const onRefreshed = vi.fn();
    render(
      <ArtifactModal
        artifact={baseArtifact}
        onClose={vi.fn()}
        onRefreshed={onRefreshed}
      />,
    );
    await userEvent.click(screen.getByTestId("artifact-refresh"));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
      expect(onRefreshed).not.toHaveBeenCalled();
    });
  });

  it("renders an <img> with data: URL for image artifacts", () => {
    const PNG_B64 =
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
    const imgArt: Artifact = {
      id: "img-1",
      kind: "image",
      title: "demo plot",
      payload: { format: "png", data_b64: PNG_B64, caption: "tiny" },
      source_kind: "python",
      source_code: "out_image()",
      updated_at: new Date().toISOString(),
    };
    render(<ArtifactModal artifact={imgArt} onClose={vi.fn()} />);
    const img = screen.getByAltText("demo plot") as HTMLImageElement;
    expect(img.src).toBe(`data:image/png;base64,${PNG_B64}`);
    expect(img.style.maxHeight).toBe("80vh");
  });

  it("hides Refresh when no source_code is present", () => {
    render(
      <ArtifactModal
        artifact={{ ...baseArtifact, source_code: null, source_kind: null }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("artifact-refresh")).toBeNull();
  });
});
