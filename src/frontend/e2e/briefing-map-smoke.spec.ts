/**
 * Cockpit map-shell smoke (spec-110 B6) — backend-free.
 *
 * Uses Playwright route-mocking (same technique as
 * web/frontend/e2e/briefing-map-smoke.spec.ts) to stub the auth +
 * game-state contract so `/game/:id` renders in a REAL browser (real
 * WebGL, unlike the jsdom Vitest tests where deck.gl is mocked). Asserts
 * the map region + lens selector mount and the route produces NO
 * uncaught page error (DeckGLMap's own render is expected to degrade
 * gracefully even on a WebGL failure).
 *
 * Needs only the cockpit Vite dev server — no live Django/Postgres, no
 * storageState — runs on the default "chromium" project.
 */
import { test, expect } from "./fixtures";

const ok = (data: unknown) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({ status: "ok", data }),
});

const SNAPSHOT = {
  tick: 3,
  session_id: "smoke",
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
  edges: [],
  events: [],
};

const SUMMARY = {
  tick: 3,
  imperial_rent: 0.3,
  avg_consciousness: 0.2,
  population_total: 120000,
  exploitation_rate: 0.4,
  profit_rate: 0.1,
  org_count: 1,
  class_count: 4,
  event_counts: { critical: 0, warning: 0, informational: 0 },
};

const COMMUNITIES = { communities: [] };

const TIMESERIES = {
  ticks: [1, 2, 3],
  imperial_rent: [0.1, 0.2, 0.3],
  consciousness: [0.1, 0.1, 0.2],
  solidarity: [0.2, 0.2, 0.3],
  heat: [0.2, 0.25, 0.3],
  wealth: [0.5, 0.5, 0.6],
  biocapacity: [0.4, 0.4, 0.4],
};

test.describe("Cockpit map shell smoke (backend-free)", () => {
  test("game route renders the map region + lens selector with no uncaught error", async ({
    page,
  }) => {
    await page.route("**/accounts/whoami/", (r) =>
      r.fulfill(ok({ is_authenticated: true, username: "smoke" })),
    );
    await page.route("**/api/games/*/state/", (r) => r.fulfill(ok(SNAPSHOT)));
    await page.route("**/api/games/*/summary/", (r) => r.fulfill(ok(SUMMARY)));
    await page.route("**/api/games/*/communities/", (r) => r.fulfill(ok(COMMUNITIES)));
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

    await page.goto("/game/smoke");
    await page.evaluate(() => document.fonts.ready);

    // The cockpit shell renders in a REAL browser — the route is
    // reachable and mounts every region.
    await expect(page.getByTestId("region-statusbar")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("region-map")).toBeVisible();
    await expect(page.getByTestId("map-mode-selector")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("tick-value")).toHaveText("3");

    // Robustness assertion: the route did NOT white-screen — no uncaught
    // exception reached the page, even with a real (possibly
    // software-rendered) WebGL context.
    expect(pageErrors, `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });
});
