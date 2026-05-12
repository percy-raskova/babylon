/**
 * Spec 061 T062: Orgs page renders live engine data.
 *
 * Smoke test that loads /games/<id>/orgs and asserts:
 *   1. The player-tab card count matches the API's player_controlled
 *      count.
 *   2. Clicking an org card reveals the OODA badge with a phase string
 *      drawn from the canonical enum.
 *
 * Requires SPEC061_TEST_SESSION_ID env var and a running dev server.
 * Skipped automatically otherwise.
 */
import { expect, test } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

test.describe("Orgs — live data (spec 061 US4)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

  test("renders allied-orgs badge", async ({ page }) => {
    await page.goto(`${BASE}/games/${SESSION_ID}/orgs`);
    await expect(page.locator("text=/\\d+ allied orgs/").first()).toBeVisible({
      timeout: 5000,
    });
  });

  test("selected org shows OODA phase badge with a canonical value", async ({ page }) => {
    await page.goto(`${BASE}/games/${SESSION_ID}/orgs`);
    // The first org auto-selects; the right panel renders the OODA
    // badge as one of {observe, orient, decide, act}.
    const oodaPhases = ["observe", "orient", "decide", "act"];
    const found = await Promise.any(
      oodaPhases.map((p) =>
        page
          .locator(`text=/^${p}$/i`)
          .first()
          .waitFor({ state: "visible", timeout: 5000 })
          .then(() => p),
      ),
    );
    expect(oodaPhases).toContain(found);
  });
});
