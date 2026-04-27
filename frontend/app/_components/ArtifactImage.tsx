"use client"

import type { Artifact, ArtifactImagePayload } from "@/lib/types"

/** Max height for plot thumbnails in chat / tool cards (modal uses fullSize). */
export const ARTIFACT_IMAGE_PREVIEW_MAX_PX = 440

export function downloadImagePng(
  payload: ArtifactImagePayload,
  filename: string
): void {
  const bin = atob(payload.data_b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  const blob = new Blob([bytes], { type: `image/${payload.format}` })
  const safe =
    (filename || "chart").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 120) + ".png"
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = safe
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function ArtifactImage({
  artifact,
  fullSize,
}: {
  artifact: Artifact
  fullSize?: boolean
}) {
  const payload = artifact.payload as ArtifactImagePayload
  if (!payload?.data_b64) {
    return (
      <div
        className="px-3.5 py-3 text-center"
        style={{ color: "var(--ink-3)" }}
      >
        No image
      </div>
    )
  }
  const src = `data:image/${payload.format};base64,${payload.data_b64}`
  return (
    <figure className="bg-card px-3.5 py-4">
      {/* next/image can't optimize a data: URL; use a plain <img>. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={artifact.title}
        style={{
          display: "block",
          margin: "0 auto",
          width: "auto",
          maxWidth: "100%",
          maxHeight: fullSize ? "80vh" : ARTIFACT_IMAGE_PREVIEW_MAX_PX,
          objectFit: "contain",
        }}
      />
      {payload.caption ? (
        <figcaption
          className="mt-1 text-center"
          style={{ fontSize: 11.5, color: "var(--ink-3)" }}
        >
          {payload.caption}
        </figcaption>
      ) : null}
    </figure>
  )
}
