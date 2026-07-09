/**
 * Placeholder E2E spec (spec-110 B1) — scaffold only.
 *
 * Intentionally skipped: B1 is scaffold-only (no feature porting), so
 * there is no real cockpit flow to drive yet. B2 replaces this skip with
 * an actual assertion once routes/screens land.
 */

import { test } from "./fixtures";

test.skip("cockpit app shell loads", async ({ page }) => {
  await page.goto("/");
});
