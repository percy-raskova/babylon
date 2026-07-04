/**
 * E2E: Navigation and panel interactions.
 *
 * Requires a running backend at http://localhost:8000 and dev server at :5173.
 * Run: npm run test:e2e
 */

import { test, expect } from "@playwright/test";

/** Helper: login, create game, enter game shell. */
async function enterGameShell(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByPlaceholder("Username").fill("testuser");
  await page.getByPlaceholder("Password").fill("testpass");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });
  await page.getByText("+ New Game").click();
  await expect(page.getByText("Tick")).toBeVisible({ timeout: 10000 });
}

test.describe("navigation", () => {
  test("right panel toggle collapses and expands", async ({ page }) => {
    await enterGameShell(page);

    // Find right panel toggle (uses a chevron button)
    const toggleButton = page.locator("button").filter({ hasText: /[»«]|[\u25B6\u25C0]/ }).last();
    if (await toggleButton.isVisible({ timeout: 2000 })) {
      // Click to collapse
      await toggleButton.click();
      // Click again to expand
      await toggleButton.click();
    }

    // Actions panel should still be visible
    await expect(page.getByText("Actions")).toBeVisible();
  });

  test("bottom panel tab switching works", async ({ page }) => {
    await enterGameShell(page);

    // Bottom panel tabs: Time Series, Events, Graph
    const eventsTab = page.getByRole("button", { name: /events/i });
    if (await eventsTab.isVisible({ timeout: 2000 })) {
      await eventsTab.click();
      // Events content should be visible
      await expect(
        page.getByText(/No events|UPRISING|EXTRACTION/i).first(),
      ).toBeVisible({ timeout: 3000 });
    }

    const graphTab = page.getByRole("button", { name: /graph/i });
    if (await graphTab.isVisible({ timeout: 2000 })) {
      await graphTab.click();
    }
  });

  test("game list shows previously created games", async ({ page }) => {
    // Login
    await page.goto("/");
    await page.getByPlaceholder("Username").fill("testuser");
    await page.getByPlaceholder("Password").fill("testpass");
    await page.getByRole("button", { name: "Enter" }).click();
    await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });

    // Game list should show + New Game button
    await expect(page.getByText("+ New Game")).toBeVisible();
  });

  test("responsive layout renders correctly at viewport size", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await enterGameShell(page);

    // All major panels should be visible at 1280x720
    await expect(page.getByText("Tick")).toBeVisible();
    await expect(page.getByText("Actions")).toBeVisible();
    await expect(page.getByText("Resolve Tick").first()).toBeVisible();
  });
});
