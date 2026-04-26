import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = process.env.E2E_BACKEND_PORT ?? "8765";
const FRONTEND_PORT = process.env.E2E_FRONTEND_PORT ?? "3765";
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;

process.env.E2E_BACKEND_URL = BACKEND_URL;
process.env.E2E_FRONTEND_URL = FRONTEND_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: FRONTEND_URL,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --port ${BACKEND_PORT} --host 127.0.0.1`,
      cwd: "../backend",
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        APP_DB_URL: "sqlite+aiosqlite:///./e2e_app.db",
        CHECKPOINT_DB_PATH: "./e2e_checkpoints.db",
      },
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT}`,
      cwd: ".",
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_BACKEND_URL_BASE: BACKEND_URL,
      },
    },
  ],
});
