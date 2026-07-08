/**
 * Spec 061 T079 / FR-021 + FR-022 / SC-012: verb composer render smoke.
 *
 * Render-only smoke: the composition page mounts with live actor/verb
 * pickers and a queue button. The FULL submit→resolve→results path is
 * driven by real-loop.spec.ts (remediation C.5 gate).
 *
 * Requires:
 *   - SPEC061_TEST_SESSION_ID env var pointing at a seeded session
 *     with at least one player-controlled organization
 *   - A running dev server (`mise run web:dev`)
 *
 * Skipped automatically when SPEC061_TEST_SESSION_ID is unset.
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

test.describe("Verb submit — live engine (spec 061 US5)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");

  test("educate composition page renders actor and verb pickers", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE}/games/${SESSION_ID}/actions/educate`);

    // The ActorPanel renders inside the "Acting Org" panel (VerbPage.tsx).
    // At least one player org should load from the live snapshot.
    await expect(page.getByText("Acting Org")).toBeVisible({ timeout: 10000 });

    // The VerbPicker renders one of the six supported verbs as the active selection.
    const supportedVerbs = ["Educate", "Reproduce", "Attack", "Mobilize", "Campaign", "Aid"];
    let foundVerb = false;
    for (const label of supportedVerbs) {
      if (
        await page
          .locator(`text=${label}`)
          .first()
          .isVisible()
          .catch(() => false)
      ) {
        foundVerb = true;
        break;
      }
    }
    expect(foundVerb).toBe(true);
  });

  test("queue button is present on the compose panel", async ({ page }) => {
    await login(page);
    await page.goto(`${BASE}/games/${SESSION_ID}/actions/educate`);
    // The ComposePanel submit button reads "Queue <verb> ▸" (VerbPage.tsx).
    const queueButton = page.getByRole("button", { name: /queue educate/i });
    await expect(queueButton).toBeVisible({ timeout: 10000 });
  });

  test("unsupported verb investigate is NOT in the verb picker", async ({ page }) => {
    // FR-025: investigate / move / negotiate are removed until follow-up spec.
    await login(page);
    await page.goto(`${BASE}/games/${SESSION_ID}/actions/educate`);
    // The VerbPicker enumerates SUPPORTED_VERBS only; investigate should be
    // absent from the picker (DISABLED_VERBS prunes it).
    const investigateLabel = page.locator("button", { hasText: /^investigate$/i });
    await expect(investigateLabel).toHaveCount(0);
  });
});
