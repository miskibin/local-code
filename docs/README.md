# Local Code — Internal Docs

Astro + [Starlight](https://starlight.astro.build) site for the local
agentic harness.

## Develop

```bash
cd docs
npm install
npm run dev          # http://localhost:4321/local-code/
```

## Build

```bash
npm run build        # outputs to ./public (publish dir for GitLab Pages)
npm run preview
```

## Deploy

Pushed to GitLab Pages by `.gitlab-ci.yml` at the repo root. The pipeline:

1. Installs deps from `docs/package-lock.json`.
2. Sets `DOCS_SITE` and `DOCS_BASE` from CI variables (`CI_PAGES_URL`,
   `CI_PROJECT_PATH`).
3. Runs `npm run build`.
4. Publishes `docs/public/` as the Pages artifact.

## Add a page

1. Create the file under `src/content/docs/...` (Markdown or MDX).
2. Add a `sidebar` entry in `astro.config.mjs` if you want it in the nav.
3. Mermaid blocks render automatically — use ` ```mermaid` fenced blocks.
