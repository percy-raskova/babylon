import { defineConfig, devices } from "@playwright/test";

// Cockpit E2E config (spec-110 B6 — the Phase-B exit gate). Port 5173 is
// the frontend's canonical dev port since the spec-112 cutover
// (vite.config.ts). Overridable via COCKPIT_E2E_PORT when the canonical
// port is squatted by a stray dev server (the B6 precedent used 5180);
// the webServer's --strictPort makes a squatter loud, never silent.
const PORT = process.env.COCKPIT_E2E_PORT ?? "5173";
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${PORT}`;

// Storage state written by e2e/auth.setup.ts. Keep this literal in sync
// with AUTH_FILE there (not imported, to avoid the setup file itself
// being pulled into every project's module graph).
const AUTH_FILE = "playwright/.auth/user.json";

// Specs that drive a real Django-backed session (login required, mutate
// or read live game state) run pre-authenticated via storageState. The
// other three (auth.spec.ts tests the login flow itself and must NOT
// start pre-authenticated; briefing-map-smoke / map-lens-cycling are
// backend-free route-mocked smokes that need no login at all) run on the
// default "chromium" project.
const AUTHENTICATED_SPECS = ["real-loop.spec.ts", "end-turn-flow.spec.ts", "verb-submit.spec.ts"];

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: AUTHENTICATED_SPECS,
    },
    {
      name: "chromium-authenticated",
      use: { ...devices["Desktop Chrome"], storageState: AUTH_FILE },
      testMatch: AUTHENTICATED_SPECS,
      dependencies: ["setup"],
    },
  ],
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    port: Number(PORT),
    reuseExistingServer: !process.env.CI,
  },
});
