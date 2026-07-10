import { defineConfig, devices } from "@playwright/test";

// Storage state written by e2e/auth.setup.ts (owner-queue item 27 /
// walkthrough G1). Keep this literal in sync with AUTH_FILE there.
const AUTH_FILE = "playwright/.auth/user.json";

// Specs that navigate straight to an authenticated `/games/:id/...` route
// without logging in first (walkthrough G1's 9 false-red secondary specs).
// They run against the "setup" project's storageState instead.
const AUTHENTICATED_SPECS = [
  "briefing-live-data.spec.ts",
  "intel-results-analysis.spec.ts",
  "orgs-live-data.spec.ts",
  "polling-tick-aligned.spec.ts",
];

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
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
    command: "npm run dev",
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },
});
