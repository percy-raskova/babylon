/**
 * E2E: authentication flow — login form, unauthenticated redirect, error
 * state, logout (spec-110 B6, mirrors web/frontend/e2e/auth.spec.ts for
 * the cockpit).
 *
 * Runs on the default (non-authenticated) "chromium" project — this spec
 * tests the login flow itself, so it must not start pre-authenticated
 * (unlike real-loop / end-turn-flow / verb-submit, which run on
 * "chromium-authenticated"). Requires the live stack: Django `:8000` +
 * the seeded admin/admin user.
 *
 * The three tests below that POST a real login are `fixme` — see
 * `auth.setup.ts`'s docstring for the exact defect (Django's
 * CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS 403s any origin but 5173).
 * The two tests that never submit the form (page-load + unauthenticated
 * redirect) are unaffected and run for real.
 */
import { test, expect } from "./fixtures";

test.describe("cockpit authentication", () => {
  test("login page loads with form fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByPlaceholder("Username")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enter" })).toBeVisible();
  });

  test("unauthenticated request to a game route redirects to /login", async ({ page }) => {
    await page.goto("/game/does-not-matter");
    await expect(page).toHaveURL(/\/login$/, { timeout: 10000 });
    await expect(page.getByPlaceholder("Username")).toBeVisible();
  });

  test.fixme("successful login redirects to the lobby", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("admin");
    await page.getByRole("button", { name: "Enter" }).click();

    await expect(page).toHaveURL(/\/lobby$/, { timeout: 10000 });
    await expect(page.getByText("New Operation")).toBeVisible();
  });

  test.fixme("invalid credentials show an inline error, no redirect", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("Username").fill("baduser");
    await page.getByPlaceholder("Password").fill("badpass");
    await page.getByRole("button", { name: "Enter" }).click();

    await expect(page.getByRole("alert")).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(/\/login$/);
  });

  test.fixme("logout returns to the login page", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("admin");
    await page.getByRole("button", { name: "Enter" }).click();
    await expect(page.getByText("New Operation")).toBeVisible({ timeout: 10000 });

    await page.getByRole("button", { name: "Logout" }).click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 10000 });
    await expect(page.getByPlaceholder("Username")).toBeVisible();
  });
});
