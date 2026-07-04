/**
 * E2E: Game loop — create game, submit actions, resolve tick.
 *
 * Requires a running backend at http://localhost:8000 and dev server at :5173.
 * Run: npm run test:e2e
 */

import { test, expect } from "@playwright/test";

/** Helper: login and navigate to game list. */
async function loginAndNavigate(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill("testuser");
  await page.getByPlaceholder("Password").fill("testpass");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });
}

test.describe("game loop", () => {
  test("create game navigates to game shell", async ({ page }) => {
    await loginAndNavigate(page);

    await page.getByText("+ New Game").click();

    // Should navigate to game shell with Tick counter
    await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });
  });

  test("game shell renders map and action panels", async ({ page }) => {
    await loginAndNavigate(page);
    await page.getByText("+ New Game").click();
    await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });

    // Map container should exist
    await expect(page.locator("canvas").first()).toBeVisible({ timeout: 5000 });

    // Action panel header
    await expect(page.getByText("Actions")).toBeVisible();

    // Resolve button
    await expect(page.getByText("Resolve Tick").first()).toBeVisible();
  });

  test("select verb and submit action", async ({ page }) => {
    await loginAndNavigate(page);
    await page.getByText("+ New Game").click();
    await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });

    // Click a verb (Educate)
    await page.getByText("Educate").click();

    // Target selector should appear
    await expect(page.getByText("Select Target")).toBeVisible({ timeout: 3000 });

    // Click first target button in the target list
    const targetButtons = page.locator("button").filter({ hasText: /entity|territory/i });
    const count = await targetButtons.count();
    if (count > 0) {
      await targetButtons.first().click();
    }

    // Submit action if preview appears
    const submitButton = page.getByText("Submit Action");
    if (await submitButton.isVisible({ timeout: 2000 })) {
      await submitButton.click();
    }
  });

  test("resolve tick shows results", async ({ page }) => {
    await loginAndNavigate(page);
    await page.getByText("+ New Game").click();
    await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });

    // Click Resolve Tick
    await page.getByText("Resolve Tick").first().click();

    // Wait for resolution to complete (button text changes during resolve)
    await expect(page.getByText("Resolving...").first()).toBeVisible({ timeout: 3000 });
    await expect(page.getByText("Resolve Tick").first()).toBeVisible({ timeout: 10000 });
  });

  test("back button returns to game list", async ({ page }) => {
    await loginAndNavigate(page);
    await page.getByText("+ New Game").click();
    await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });

    // Click back arrow
    await page.getByText("Games").click();

    // Should return to game list
    await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });
  });
});
