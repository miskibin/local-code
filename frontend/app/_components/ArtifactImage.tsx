"use client"

import type { Artifact, ArtifactImagePayload } from "@/lib/types"

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
    <figure className="bg-white px-3.5 py-3">
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
          maxHeight: fullSize ? "80vh" : 280,
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
