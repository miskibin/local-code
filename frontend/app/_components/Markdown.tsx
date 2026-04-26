"use client"

import type { ComponentProps } from "react"
import { Streamdown, defaultUrlTransform } from "streamdown"
import { cjk } from "@streamdown/cjk"
import { code } from "@streamdown/code"
import { math } from "@streamdown/math"
import { mermaid } from "@streamdown/mermaid"
import { ArtifactChip } from "./ArtifactRefs"

const streamdownPlugins = { cjk, code, math, mermaid }

const ARTIFACT_PREFIX = "artifact:"

const urlTransform: ComponentProps<typeof Streamdown>["urlTransform"] = (
  url,
  key,
  node
) => {
  if (typeof url === "string" && url.startsWith(ARTIFACT_PREFIX)) return url
  return defaultUrlTransform(url, key, node)
}

const components: ComponentProps<typeof Streamdown>["components"] = {
  a: ({ href, children, ...rest }) => {
    if (typeof href === "string" && href.startsWith(ARTIFACT_PREFIX)) {
      const id = href.slice(ARTIFACT_PREFIX.length).trim()
      if (id) return <ArtifactChip id={id} label={children} />
    }
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  },
}

export function Markdown({ text }: { text: string }) {
  return (
    <div
      className="lc-markdown text-[15px]"
      style={{ color: "var(--ink)", lineHeight: "var(--density-line)" }}
    >
      <Streamdown
        plugins={streamdownPlugins}
        components={components}
        urlTransform={urlTransform}
      >
        {text}
      </Streamdown>
    </div>
  )
}
