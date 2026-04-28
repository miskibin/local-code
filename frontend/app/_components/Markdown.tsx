"use client"

import type { ComponentProps } from "react"
import { Streamdown } from "streamdown"
import { cjk } from "@streamdown/cjk"
import { code } from "@streamdown/code"
import { math } from "@streamdown/math"
import { mermaid } from "@streamdown/mermaid"
import { InlineArtifact } from "./ArtifactRefs"

const streamdownPlugins = { cjk, code, math, mermaid }

const ARTIFACT_PREFIX = "artifact:"
const UNSAFE_HREF = /^(javascript|data|vbscript):/i

const urlTransform: ComponentProps<typeof Streamdown>["urlTransform"] = (url) =>
  url

const linkSafety: ComponentProps<typeof Streamdown>["linkSafety"] = {
  enabled: false,
}

const rehypePlugins: ComponentProps<typeof Streamdown>["rehypePlugins"] = []

const components: ComponentProps<typeof Streamdown>["components"] = {
  p: ({ node: _node, children, ...rest }) => (
    <div data-lc-md-p {...rest}>
      {children}
    </div>
  ),
  a: ({ href, children, ...rest }) => {
    if (typeof href === "string" && href.startsWith(ARTIFACT_PREFIX)) {
      const id = href.slice(ARTIFACT_PREFIX.length).trim()
      if (id) return <InlineArtifact id={id} />
    }
    const safeHref =
      typeof href === "string" && UNSAFE_HREF.test(href) ? undefined : href
    return (
      <a href={safeHref} target="_blank" rel="noreferrer" {...rest}>
        {children}
      </a>
    )
  },
}

/** Disables Streamdown linkSafety + default rehype-harden (`[blocked]` on custom protocols). */
export const trustedStreamdownMarkdownProps: Pick<
  ComponentProps<typeof Streamdown>,
  "urlTransform" | "linkSafety" | "rehypePlugins" | "components"
> = {
  urlTransform,
  linkSafety,
  rehypePlugins,
  components,
}

export function Markdown({ text }: { text: string }) {
  return (
    <div
      className="lc-markdown text-[15px]"
      style={{ color: "var(--ink)", lineHeight: "var(--density-line)" }}
    >
      <Streamdown
        plugins={streamdownPlugins}
        {...trustedStreamdownMarkdownProps}
      >
        {text}
      </Streamdown>
    </div>
  )
}
