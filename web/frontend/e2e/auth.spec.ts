/**
 * E2E: Authentication flow.
 *
 * Requires a running backend at http://localhost:8000 and dev server at :5173.
 * Run: npm run test:e2e
 */

import { test, expect } from "@playwright/test";

test.describe("authentication", () => {
  test("login page loads with form fields", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByPlaceholder("Username")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Log In" })).toBeVisible();
  });

  test("successful login redirects to game list", async ({ page }) => {
    await page.goto("/");

    await page.getByPlaceholder("Username").fill("testuser");
    await page.getByPlaceholder("Password").fill("testpass");
    await page.getByRole("button", { name: "Log In" }).click();

    // Should see game list after login
    await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });
  });

  test("invalid credentials show error message", async ({ page }) => {
    await page.goto("/");

    await page.getByPlaceholder("Username").fill("baduser");
    await page.getByPlaceholder("Password").fill("badpass");
    await page.getByRole("button", { name: "Log In" }).click();

    // Should see error message
    await expect(page.locator("[class*='text-crimson']")).toBeVisible({ timeout: 5000 });
  });

  test("logout returns to login page", async ({ page }) => {
    // Login first
    await page.goto("/");
    await page.getByPlaceholder("Username").fill("testuser");
    await page.getByPlaceholder("Password").fill("testpass");
    await page.getByRole("button", { name: "Log In" }).click();
    await expect(page.getByText("Your Games")).toBeVisible({ timeout: 5000 });

    // Logout
    await page.getByRole("button", { name: "Logout" }).click();

    // Should return to login
    await expect(page.getByPlaceholder("Username")).toBeVisible({ timeout: 5000 });
  });
});
