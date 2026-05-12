/**
 * Spec 061 T128 / FR-028: polling cadence keeps v2 pages aligned with engine ticks.
 *
 * The Briefing/Orgs/Analysis pages poll every POLL_INTERVAL_MS (2s).
 * This test asserts that when the backend advances the tick (via
 * /resolve/), the page's displayed tick number updates within 4 seconds
 * (2× the polling interval).
 *
 * Requires SPEC061_TEST_SESSION_ID set to a session that can be
 * resolved (i.e., has player actions queued or is in a resolvable
 * state). Skipped automatically when the env var isn't set.
 */
import { expect, request, test } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";
const API_BASE = process.env.SPEC061_API_BASE ?? "http://localhost:8000";

test.describe("Polling cadence (spec 061 FR-028)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

  test("Briefing page tick updates within 4 s of /resolve/", async ({ page }) => {
    await page.goto(`${BASE}/games/${SESSION_ID}`);

    // Capture the current tick from the subtitle.
    const tickRegex = /Tick (\d+)/;
    const initialText = await page.locator("text=/Tick \\d+/").first().textContent();
    const initial = parseInt(initialText?.match(tickRegex)?.[1] ?? "0", 10);

    // Advance the tick server-side.
    const apiContext = await request.newContext();
    const resp = await apiContext.post(`${API_BASE}/api/games/${SESSION_ID}/resolve/`);
    expect(resp.ok()).toBeTruthy();

    // The page polls every 2 s; assert the displayed tick advances
    // within 4 s (allow one missed poll).
    await expect
      .poll(
        async () => {
          const txt = await page.locator("text=/Tick \\d+/").first().textContent();
          return parseInt(txt?.match(tickRegex)?.[1] ?? "0", 10);
        },
        { timeout: 4_500, intervals: [500, 1000, 1500] },
      )
      .toBeGreaterThan(initial);
  });
});
