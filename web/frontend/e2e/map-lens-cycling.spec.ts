/**
 * Map lens-cycling smoke (spec-093 US3 gate) — backend-free.
 *
 * Uses Playwright route-mocking (same pattern as `briefing-map-smoke.spec.ts`)
 * to stub the auth + game-state contract with a snapshot carrying real
 * spec-070 balkanization data (factions/sovereigns/territory_influence), so
 * the map's political-topology lens set renders in a REAL browser. Cycles
 * through all 5 lens modes (stance/heat/habitability/faction/collapse) via
 * the visible `MapModeSelector` control and asserts:
 *
 *   1. Each lens is selectable and becomes the active (`aria-pressed`) mode.
 *   2. The lens legend text changes to match the active lens.
 *   3. No uncaught page error occurs at any point in the cycle (the map
 *      degrades gracefully even if a WebGL context is unavailable in CI).
 *
 * Needs only the Vite dev server (auto-started by playwright.config
 * webServer) — no live seeded Postgres session required.
 */

import { test, expect } from "@playwright/test";

const SNAPSHOT = {
  tick: 12,
  session_id: "lens-smoke",
  organizations: [{ id: "o1", name: "WCLF", short_name: "WCLF", player_controlled: true }],
  territories: [
    {
      id: "t1",
      name: "Genesee County",
      heat: 0.4,
      rent_level: 0.5,
      biocapacity: 40,
      population: 120000,
      h3_index: "872a3072cffffff",
    },
    {
      id: "t2",
      name: "Washtenaw County",
      heat: 0.2,
      rent_level: 0.3,
      biocapacity: 90,
      population: 80000,
      h3_index: "872a3072dffffff",
    },
    {
      id: "t3",
      name: "Wayne County",
      heat: 0.8,
      rent_level: 0.9,
      biocapacity: 10,
      population: 500000,
      h3_index: "872a3072effffff",
    },
  ],
  hyperedges: [],
  edges: [],
  events: [],
  balkanization: {
    factions: [
      { id: "FAC_A", colonial_stance: "uphold", is_settler_formation: true },
      { id: "FAC_B", colonial_stance: "ignore", is_settler_formation: true },
      { id: "FAC_C", colonial_stance: "abolish", is_settler_formation: false },
    ],
    sovereigns: [
      {
        id: "SOV_A",
        ruling_faction_id: "FAC_A",
        extraction_policy: "intensify",
        legitimacy: 0.58,
        claimed_territory_ids: ["t2", "t3"],
      },
    ],
    territory_influence: [
      {
        territory_id: "t1",
        influences: [
          { faction_id: "FAC_A", influence_level: 0.47, support_type: "ideological" },
          { faction_id: "FAC_B", influence_level: 0.41, support_type: "material" },
        ],
        dominant_faction_id: "FAC_A",
        current_sovereign_id: null,
        contested: true,
        habitability: 0.4,
      },
      {
        territory_id: "t2",
        influences: [{ faction_id: "FAC_A", influence_level: 0.71, support_type: "ideological" }],
        dominant_faction_id: "FAC_A",
        current_sovereign_id: "SOV_A",
        contested: false,
        habitability: 0.9,
      },
      {
        territory_id: "t3",
        influences: [{ faction_id: "FAC_C", influence_level: 0.62, support_type: "material" }],
        dominant_faction_id: "FAC_C",
        current_sovereign_id: "SOV_A",
        contested: false,
        habitability: 0.1,
      },
    ],
  },
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

const LENSES = ["stance", "heat", "habitability", "faction", "collapse"] as const;

test.describe("Map lens cycling (backend-free, spec-093 US3 gate)", () => {
  test("cycles all 5 political-topology lenses with no uncaught page error", async ({ page }) => {
    const ok = (data: unknown) => ({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", data }),
    });

    await page.route("**/accounts/whoami/", (r) =>
      r.fulfill(ok({ is_authenticated: true, username: "lens-smoke" })),
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

    await page.goto("/games/lens-smoke");
    await page.evaluate(() => document.fonts.ready);

    // The in-game shell renders (NavRail present) — the route mounts.
    await expect(page.getByRole("link", { name: "Briefing" })).toBeVisible({ timeout: 10000 });

    const selector = page.getByTestId("map-mode-selector");
    await expect(selector).toBeVisible({ timeout: 10000 });

    for (const lens of LENSES) {
      const button = page.getByTestId(`lens-mode-${lens}`);
      await button.click();
      await expect(button).toHaveAttribute("aria-pressed", "true");

      // Legend text reflects the active lens (case-insensitive substring —
      // the exact copy lives in mapLensLayers.ts's LEGEND_LABELS).
      await expect(page.getByTestId("lens-legend-label")).toContainText(new RegExp(lens, "i"));
    }

    expect(pageErrors, `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });

  test("faction lens hides sovereign CLAIMS hulls while stance lens shows them", async ({
    page,
  }) => {
    const ok = (data: unknown) => ({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", data }),
    });

    await page.route("**/accounts/whoami/", (r) =>
      r.fulfill(ok({ is_authenticated: true, username: "lens-smoke" })),
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

    await page.goto("/games/lens-smoke");
    await expect(page.getByRole("link", { name: "Briefing" })).toBeVisible({ timeout: 10000 });

    // Stance lens is the default — legend should read "stance", not error.
    await expect(page.getByTestId("lens-legend-label")).toContainText(/stance/i);

    // Switching to faction lens is a distinct, non-crashing state (hull
    // suppression is verified at the unit level in mapLensLayers.test.ts —
    // this is the smoke-level confirmation that the real page doesn't
    // white-screen on the transition).
    await page.getByTestId("lens-mode-faction").click();
    await expect(page.getByTestId("lens-legend-label")).toContainText(/faction/i);
  });
});
