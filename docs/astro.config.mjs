// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import mermaid from "astro-mermaid";

// GitLab Pages serves project sites at https://<group>.gitlab.io/<project>/.
// Override via DOCS_BASE / DOCS_SITE in CI when the project slug differs.
const SITE = process.env.DOCS_SITE ?? "https://example.gitlab.io";
const BASE = process.env.DOCS_BASE ?? "/local-code";

export default defineConfig({
  site: SITE,
  base: BASE,
  outDir: "./public",
  publicDir: "./static",
  trailingSlash: "ignore",
  integrations: [
    mermaid({
      theme: "dark",
      autoTheme: true,
    }),
    starlight({
      title: "Local Code — Internal Docs",
      description:
        "Architecture & contributor guide for the local Gemma agentic harness.",
      logo: { src: "./src/assets/logo.svg", replacesTitle: false },
      customCss: ["./src/styles/custom.css"],
      lastUpdated: true,
      pagination: true,
      social: [
        {
          icon: "gitlab",
          label: "GitLab",
          href: "https://gitlab.com/",
        },
      ],
      sidebar: [
        {
          label: "Start here",
          items: [
            { label: "Overview", slug: "overview" },
            { label: "Architecture map", slug: "architecture" },
            { label: "How a turn works", slug: "request-lifecycle" },
            { label: "Local development", slug: "development" },
          ],
        },
        {
          label: "Modules",
          items: [
            { label: "Core", slug: "modules/core" },
            { label: "Commands", slug: "modules/commands" },
            { label: "Tools", slug: "modules/tools" },
            { label: "MCPs", slug: "modules/mcps" },
            { label: "Streaming", slug: "modules/streaming" },
            { label: "Persistence", slug: "modules/persistence" },
            { label: "Frontend", slug: "modules/frontend" },
          ],
        },
        {
          label: "How-to (extend)",
          items: [
            { label: "Add a tool", slug: "guides/add-a-tool" },
            { label: "Add a slash command", slug: "guides/add-a-command" },
            { label: "Register an MCP server", slug: "guides/add-an-mcp" },
            { label: "Add a subagent", slug: "guides/add-a-subagent" },
            { label: "Render a custom tool UI", slug: "guides/render-tool-ui" },
          ],
        },
        {
          label: "Reference",
          items: [
            { label: "REST routes", slug: "reference/routes" },
            { label: "Conventions", slug: "reference/conventions" },
          ],
        },
      ],
    }),
  ],
});
