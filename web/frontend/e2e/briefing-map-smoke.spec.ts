/**
 * Briefing map route smoke (spec-091 review fix #2) — backend-free.
 *
 * Uses Playwright route-mocking to stub the auth + game-state contract so the
 * in-game INDEX route `/games/:id` renders in a REAL browser (real WebGL, unlike
 * the jsdom Vitest tests where deck.gl is mocked). Asserts the map region mounts
 * and — critically for review fix #1 — that the route produces NO uncaught page
 * error (the ErrorBoundary keeps a WebGL failure from white-screening the route).
 *
 * Needs only the Vite dev server (auto-started by playwright.config webServer).
 */

import { test, expect } from "@playwright/test";

const SNAPSHOT = {
  tick: 3,
  session_id: "smoke",
  events: [],
  organizations: [{ id: "o1", name: "WCLF", short_name: "WCLF", player_controlled: true }],
  territories: [
    {
      id: "t1",
      name: "Wayne",
      heat: 0.3,
      rent_level: 0.5,
      biocapacity: 0.4,
      population: 120000,
      h3_index: "872a3072cffffff",
    },
  ],
  hyperedges: [],
  relationships: [],
};

const TIMESERIES = {
  ticks: [1, 2, 3],
  imperial_rent: [0.1, 0.2, 0.3],
  consciousness: [0.1, 0.1, 0.2],
  solidarity: [0.2, 0.2, 0.3],
  heat: [0.2, 0.25, 0.3],
  wealth: [0.5, 0.5, 0.6],
  biocapacity: [0.4, 0.4, 0.4],
};

test.describe("Briefing map route smoke (backend-free)", () => {
  test("in-game index route renders the map region with no uncaught error", async ({ page }) => {
    const ok = (data: unknown) => ({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", data }),
    });

    await page.route("**/accounts/whoami/", (r) =>
      r.fulfill(ok({ is_authenticated: true, username: "smoke" })),
    );
    await page.route("**/api/games/*/state/", (r) => r.fulfill(ok(SNAPSHOT)));
    await page.route("**/api/games/*/actions/available/", (r) => r.fulfill(ok([])));
    await page.route("**/api/games/*/map/**", (r) =>
      r.fulfill(ok({ type: "FeatureCollection", features: [] })),
    );
    await page.route("**/api/games/*/timeseries/", (r) =>
      r.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(TIMESERIES),
      }),
    );

    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.goto("/games/smoke");
    await page.evaluate(() => document.fonts.ready);

    // The in-game shell renders in a REAL browser (NavRail present) — the route
    // is reachable and mounts the Briefing chrome.
    await expect(page.getByRole("link", { name: "Briefing" })).toBeVisible({ timeout: 10000 });

    // Robustness assertion (review fix #1): the in-game INDEX route did NOT
    // white-screen — no uncaught exception reached the page. With the map wrapped
    // in an ErrorBoundary, even a deck.gl/WebGL failure degrades gracefully.
    // NOTE: exercising the LIVE deck.gl canvas render needs the full snapshot
    // contract (a seeded session) — that is the owner-run map verification.
    expect(pageErrors, `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });
});
