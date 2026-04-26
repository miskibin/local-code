import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { Markdown } from "@/app/_components/Markdown"

describe("Markdown link behavior", () => {
  it("renders http(s) URLs as plain anchors with no safety-modal button", () => {
    const { container } = render(
      <Markdown text="see [example](https://example.com) for details" />
    )
    const anchors = container.querySelectorAll("a")
    expect(anchors.length).toBe(1)
    const a = anchors[0] as HTMLAnchorElement
    expect(a.getAttribute("href")).toMatch(/^https:\/\/example\.com\/?$/)
    expect(a.textContent).toBe("example")
    expect(
      container.querySelectorAll('button[data-streamdown="link"]').length
    ).toBe(0)
  })

  it("renders bare URL autolinks without a safety modal", () => {
    const { container } = render(
      <Markdown text="visit https://anthropic.com directly" />
    )
    const anchors = container.querySelectorAll("a")
    expect(anchors.length).toBe(1)
    expect(anchors[0].getAttribute("href")).toMatch(
      /^https:\/\/anthropic\.com\/?$/
    )
    expect(
      container.querySelectorAll('button[data-streamdown="link"]').length
    ).toBe(0)
  })

  it("renders artifact: protocol mentions as a chip button", () => {
    const { container } = render(
      <Markdown text="see [chart](artifact:art_abc123) above" />
    )
    const chip = container.querySelector('button[title="art_abc123"]')
    expect(chip).not.toBeNull()
    expect(container.querySelector("span.text-gray-500")).toBeNull()
  })

  it("does not block uncommon protocols (file://, ftp://)", () => {
    const { container } = render(
      <Markdown text="open [local](file:///tmp/x) and [old](ftp://example.com)" />
    )
    const hrefs = Array.from(container.querySelectorAll("a")).map((a) =>
      a.getAttribute("href")
    )
    expect(hrefs.some((h) => h?.startsWith("file:"))).toBe(true)
    expect(hrefs.some((h) => h?.startsWith("ftp:"))).toBe(true)
  })

  it("blocks javascript: hrefs as a basic XSS guard", () => {
    const { container } = render(
      <Markdown text='[click](javascript:alert(1))' />
    )
    const a = container.querySelector("a")
    expect(a).not.toBeNull()
    expect(a?.getAttribute("href")).toBeNull()
  })
})
