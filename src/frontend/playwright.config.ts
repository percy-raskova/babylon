import { defineConfig, devices } from "@playwright/test";

// Cockpit E2E config (spec-110 B1) — port 5174, mirrors web/frontend's
// playwright.config.ts shape. The auth storageState fixture lives in
// e2e/fixtures.ts; no real specs run against it yet (B2 wires the login
// flow and swaps the placeholder skip for real assertions).
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5174",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    port: 5174,
    reuseExistingServer: !process.env.CI,
  },
});
