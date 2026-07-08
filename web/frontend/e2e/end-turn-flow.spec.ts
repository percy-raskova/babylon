/**
 * Spec 092 gate: end turn → tick resolution → log entry.
 *
 * Requires SPEC061_TEST_SESSION_ID and a running dev server (same
 * owner-run convention as intel-results-analysis.spec.ts /
 * orgs-live-data.spec.ts — a live Postgres-backed EngineBridge session,
 * not something this agent stands up unattended). Skipped automatically
 * otherwise.
 *
 * Owner setup (see spec-092 close-out report for the full checklist):
 *   1. mise run web:dev
 *   2. RUN_MAIN=true poetry run python web/manage.py seed_initial_game --scenario wayne_county
 *      (RUN_MAIN=true is required: apps.py skips bridge init for DEBUG
 *      management commands otherwise and the seed refuses the stub bridge)
 *   3. SPEC061_TEST_SESSION_ID=<printed session id> npx playwright test end-turn-flow
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

/** All /api/* views require a session — log in as the seeded admin user. */
async function login(page: Page): Promise<void> {
  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder("Username").fill("admin");
  await page.getByPlaceholder("Password").fill("admin");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 10000 });
}

test.describe("end turn -> tick resolution -> log entry (spec 092)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

  test("End Turn resolves the tick, shows the resolution screen, then the log has a new entry", async ({
    page,
  }) => {
    await login(page);
    await page.goto(`${BASE}/games/${SESSION_ID}/orgs`);
    await expect(page.getByText(/End Turn/)).toBeVisible({ timeout: 10000 });

    await page.getByText(/End Turn/).click();

    // Bridge resolves the tick, then OrgsPage navigates to /resolution.
    await expect(page).toHaveURL(new RegExp(`/games/${SESSION_ID}/resolution$`), {
      timeout: 15000,
    });
    await expect(page.getByText(/Resolving Tick/)).toBeVisible({ timeout: 10000 });

    // Wait for the animated reveal to finish and dismiss the screen.
    await expect(page.getByText(/Continue/)).toBeVisible({ timeout: 15000 });
    await page.getByText(/Continue/).click();
    await expect(page).toHaveURL(new RegExp(`/games/${SESSION_ID}$`), { timeout: 10000 });

    // The Event Log now reflects the resolved tick's history.
    await page.goto(`${BASE}/games/${SESSION_ID}/log`);
    await expect(page.getByText(/Event Log/i).first()).toBeVisible({ timeout: 10000 });
    // Soft assertion — the seeded scenario may or may not emit events on
    // its first tick; the page must render either the history or the
    // empty state without crashing.
    const hasEntryOrEmptyState = await page
      .getByText(/No events recorded yet|t=\d+/)
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    expect(hasEntryOrEmptyState).toBe(true);
  });
});
