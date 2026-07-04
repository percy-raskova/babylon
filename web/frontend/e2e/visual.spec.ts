/**
 * Visual-baseline suite — pins the Cold Collapse canon (spec-090 residual b).
 *
 * Deterministic by construction: fixed viewport, animations disabled, fonts
 * awaited (self-hosted OFL faces, no runtime web-font fetch). The login route
 * renders backend-free (the whoami probe fails → LoginPage), so this suite
 * needs only the Vite dev server (auto-started by playwright.config webServer).
 *
 * R-CRT: the login screen is CHROME — diegetic CRT/bunker texture is permitted
 * here. This suite deliberately snapshots chrome only; no data-encoding surface
 * (chart plot / map fill / ramp) is captured, where luminance-monotonic ramps
 * bind absolutely and texture is forbidden.
 */

import { test, expect } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("Cold Collapse visual canon", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Self-hosted fonts must be resolved before we snapshot or read metrics.
    await page.evaluate(() => document.fonts.ready);
    await expect(page.getByPlaceholder("Username")).toBeVisible();
  });

  test("login chrome matches the Cold Collapse baseline", async ({ page }) => {
    await expect(page).toHaveScreenshot("login-chrome.png", {
      animations: "disabled",
      caret: "hide",
      fullPage: true,
    });
  });

  test("canon palette + type stack are live on :root", async ({ page }) => {
    const tokens = await page.evaluate(() => {
      const s = getComputedStyle(document.documentElement);
      return {
        spire: s.getPropertyValue("--babylon-spire").trim(),
        rupture: s.getPropertyValue("--babylon-rupture").trim(),
        solidarity: s.getPropertyValue("--babylon-solidarity").trim(),
        sans: s.getPropertyValue("--font-sans").trim(),
        mono: s.getPropertyValue("--font-mono").trim(),
      };
    });
    // Cyan-spire primary; gold demoted to the scarce rupture accent.
    expect(tokens.spire.toLowerCase()).toBe("#4dd9e6");
    expect(tokens.rupture.toLowerCase()).toBe("#d4a02c");
    expect(tokens.solidarity.toLowerCase()).toBe("#5fbf7a");
    // Self-hosted Cold Collapse type stack — no Inter / Roboto Mono.
    expect(tokens.sans).toContain("Space Grotesk");
    expect(tokens.mono).toContain("JetBrains Mono");
    expect(`${tokens.sans} ${tokens.mono}`).not.toMatch(/Inter|Roboto Mono/);
  });
});
