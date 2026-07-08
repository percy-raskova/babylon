/**
 * E2E: Authentication flow + games-list rendering.
 *
 * Requires a running backend at http://localhost:8000 and dev server at
 * :5173, with the seeded admin/admin user (seed_initial_game creates it;
 * password == username).
 * Run: npm run test:e2e
 */

import { test, expect } from "@playwright/test";

test.describe("authentication", () => {
  test("login page loads with form fields", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByPlaceholder("Username")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enter" })).toBeVisible();
  });

  test("successful login redirects to the operations list", async ({ page }) => {
    await page.goto("/");

    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("admin");
    await page.getByRole("button", { name: "Enter" }).click();

    // Should see the operations list after login (GameList.tsx panel titles).
    await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("New Operation")).toBeVisible();
    // The seeded game card renders — the exact regression bug #1
    // (snapshot_json orphan) caused: GET /api/games/ answered 500 and the
    // list stayed empty.
    await expect(page.getByText("wayne_county", { exact: true }).first()).toBeVisible();
  });

  test("invalid credentials show error message", async ({ page }) => {
    await page.goto("/");

    await page.getByPlaceholder("Username").fill("baduser");
    await page.getByPlaceholder("Password").fill("badpass");
    await page.getByRole("button", { name: "Enter" }).click();

    // Should see error message
    await expect(page.locator("[class*='text-crimson']")).toBeVisible({ timeout: 5000 });
  });

  test("logout returns to login page", async ({ page }) => {
    // Login first
    await page.goto("/");
    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("admin");
    await page.getByRole("button", { name: "Enter" }).click();
    await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 5000 });

    // Logout
    await page.getByRole("button", { name: "Logout" }).click();

    // Should return to login
    await expect(page.getByPlaceholder("Username")).toBeVisible({ timeout: 5000 });
  });
});
