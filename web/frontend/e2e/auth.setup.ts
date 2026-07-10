/**
 * Playwright auth setup project (owner-queue item 27 / walkthrough G1).
 *
 * Logs in once through the real Django login form (same flow
 * `real-loop.spec.ts` drives per-test) and persists the authenticated
 * browser storage state to disk. Spec projects that `dependencies: ["setup"]`
 * and set `use.storageState` to `AUTH_FILE` start every test already
 * logged in, instead of landing on `/login` and false-redding.
 *
 * Requires the same live stack as the specs it unblocks: Django `:8000`
 * (RUN_MAIN=true) + Vite `:5173` + the seeded admin/admin user
 * (seed_initial_game). Skipped automatically without
 * SPEC061_TEST_SESSION_ID, matching the convention every session-gated
 * e2e spec in this directory already follows.
 */
import { test as setup, expect } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

/** Where the authenticated storage state is written; consumed via `use.storageState`. */
export const AUTH_FILE = "playwright/.auth/user.json";

setup.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

setup("authenticate", async ({ page }) => {
  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder("Username").fill("admin");
  await page.getByPlaceholder("Password").fill("admin");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 10000 });

  await page.context().storageState({ path: AUTH_FILE });
});
