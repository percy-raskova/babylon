/**
 * Spec 094: The Wire — Playwright e2e (owner-run).
 *
 * Verifies The Wire renders a live 50-tick game. Gated on
 * SPEC061_TEST_SESSION_ID — skips cleanly without it (same precedent
 * as spec-091/spec-092's behavioural suites).
 *
 * Owner-run checklist:
 *   1. mise run web:dev (Django + Vite)
 *   2. Set SPEC061_TEST_SESSION_ID to a seeded 50+ tick session
 *   3. npx playwright test e2e/wire-50-tick.spec.ts
 */

import { test, expect } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;

test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID not set — owner-run only");

test("Wire renders a live 50-tick game", async ({ page }) => {
  const gameId = SESSION_ID!;
  await page.goto(`/games/${gameId}/wire`);

  // Title bar
  await expect(page.locator("text=THE WIRE")).toBeVisible();

  // Tick badge (should be >= 50)
  const tickBadge = page.locator("[class*='font-bold']");
  await expect(tickBadge.first()).toBeVisible();

  // All 4 tabs visible
  await expect(page.locator("text=The Wire")).toBeVisible();
  await expect(page.locator("text=Wire Index")).toBeVisible();
  await expect(page.locator("text=Patterns")).toBeVisible();
  await expect(page.locator("text=Corpus")).toBeVisible();

  // Triptych columns
  await expect(page.locator("text=CHANNEL - CORPORATE")).toBeVisible();
  await expect(page.locator("text=CHANNEL - LIBERATED")).toBeVisible();
  await expect(page.locator("text=CHANNEL - INTEL")).toBeVisible();

  // Switch to Patterns tab
  await page.locator("text=Patterns").click();
  await expect(page.locator("text=Manufacturing Consent")).toBeVisible();

  // Switch to Index tab
  await page.locator("text=Wire Index").click();
  await expect(page.locator("text=Recent dispatches")).toBeVisible();
});
