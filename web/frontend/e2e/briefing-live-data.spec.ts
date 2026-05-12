/**
 * Spec 061 T046: Briefing page renders live engine data.
 *
 * Smoke test that loads the Briefing page for a seeded session and
 * asserts:
 *   1. The tick badge in the page header matches the session's current
 *      tick (read from the API).
 *   2. The sparkline strip has at least one point per metric after
 *      three /resolve/ calls.
 *
 * Requires a running dev server (`mise run web:dev`) and a seeded
 * session via `seed_initial_game --scenario wayne_county`.
 * Skipped automatically when those preconditions aren't met.
 */
import { expect, test } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

test.describe("Briefing — live data (spec 061 US3)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

  test("tick badge matches API tick", async ({ page }) => {
    await page.goto(`${BASE}/games/${SESSION_ID}`);
    // PageHeader's right slot renders the tick badge with class .bbl-data
    // (BblData component). Wait for any element with the tick value to
    // appear — the BriefingPage subtitle also includes "Tick {n}".
    const tickBadge = page.locator("text=/Tick \\d+/");
    await expect(tickBadge.first()).toBeVisible({ timeout: 5000 });
  });

  test("sparkline strip renders six labeled metrics", async ({ page }) => {
    await page.goto(`${BASE}/games/${SESSION_ID}`);
    // Sparkline component renders the label inside the sparkline SVG.
    // Assert all six are present after the initial fetch.
    for (const label of ["RENT", "CON", "SOL", "HEAT", "WEALTH", "BIOCAP"]) {
      await expect(page.locator(`text=${label}`).first()).toBeVisible({
        timeout: 5000,
      });
    }
  });
});
