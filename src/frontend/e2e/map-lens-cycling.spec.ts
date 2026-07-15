/**
 * Map lens-cycling smoke (spec-110 B6; lens roster + default rewritten
 * spec-113 Lane B) — backend-free.
 *
 * Cockpit port of web/frontend/e2e/map-lens-cycling.spec.ts: route-mocks
 * (same technique as briefing-map-smoke.spec.ts) the auth + game-state +
 * map-snapshot contracts — the map-snapshot mock carries the spec-070
 * balkanization data (factions/sovereigns/territory_influence) under
 * `metadata.balkanization`, matching `EngineBridge.get_map_snapshot`'s
 * real response shape — so the full lens set renders in a REAL browser.
 * `/geo/counties.topojson`/`states.topojson`/`basemap-style.json`
 * (Lane Carto) are NOT route-mocked — they're real static assets under
 * `public/geo/`, served by the Vite dev server directly.
 *
 * DEVIATION (deliberate, spec-113 Lane B): the lens roster changed from the
 * 5 spec-093 political-topology modes to the full `LENS_REGISTRY`
 * (`lib/lenses/registry.ts`) — imperial_rent/exploitation_rate/heat/
 * solidarity_index/stance/faction/collapse/class_composition/habitability
 * — and the DEFAULT lens changed from "stance" to "imperial_rent"
 * (DESIGN_BIBLE.md §9 amendment 1). Every assertion below that depended on
 * either fact is updated; testids (`map-mode-selector`, `lens-mode-<id>`,
 * `lens-legend-label`) are unchanged.
 *
 * Wave 2 Round 2 (`reports/wave2-implementation-map.md`) adds three more
 * registry entries — throughput_position/agitation (numeric metric lenses)
 * and territory_type (the new dedicated categorical lens kind, the real
 * `TerritoryType` enum) — bringing the roster to 12. `hasMetric`-gated like
 * solidarity_index/class_composition, but this file's mock `/map/` response
 * never sets `metadata.available_metrics`, so `availableLensRegistry`'s
 * "undefined means available" rule (registry.ts) keeps all three visible
 * here regardless.
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
};

const SUMMARY = {
  tick: 12,
  imperial_rent: 0.4,
  avg_consciousness: 0.3,
  population_total: 700000,
  exploitation_rate: 0.5,
  profit_rate: 0.2,
  org_count: 1,
  class_count: 4,
  event_counts: { critical: 0, warning: 0, informational: 0 },
};

const COMMUNITIES = { communities: [] };

// Spec-093: the balkanization block lives under GET /api/games/{id}/map/'s
// `metadata.balkanization` (EngineBridge.get_map_snapshot ->
// _build_balkanization_block) — NOT on the /state/ snapshot.
const BALKANIZATION = {
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
};

const MAP_DATA = {
  type: "FeatureCollection",
  features: [],
  metadata: { balkanization: BALKANIZATION },
};

const TIMESERIES = {
  ticks: [10, 11, 12],
  imperial_rent: [0.1, 0.2, 0.3],
  consciousness: [0.1, 0.1, 0.2],
  solidarity: [0.2, 0.2, 0.3],
  heat: [0.2, 0.25, 0.3],
  wealth: [0.5, 0.5, 0.6],
  biocapacity: [0.4, 0.4, 0.4],
};

/**
 * Registry order (`lib/lenses/registry.ts`'s `LENS_REGISTRY`) — id + the
 * expected `lens-legend-label` substring (independently stated, not read
 * back from the app, per the token-contract "residual-e" discipline: a
 * regression that repoints a lens's label fails here instead of silently
 * passing a read-back tautology). imperial_rent is index 0 — THE DEFAULT.
 */
const LENSES = [
  { id: "imperial_rent", label: /imperial rent/i },
  { id: "exploitation_rate", label: /exploitation rate/i },
  { id: "throughput_position", label: /throughput/i },
  { id: "heat", label: /heat/i },
  { id: "solidarity_index", label: /solidarity/i },
  { id: "agitation", label: /agitation/i },
  { id: "stance", label: /stance/i },
  { id: "faction", label: /faction/i },
  { id: "collapse", label: /collapse/i },
  { id: "class_composition", label: /class composition/i },
  { id: "territory_type", label: /territory type/i },
  { id: "habitability", label: /habitability/i },
] as const;

/**
 * Known sandbox-environment WebGL limitation (documented independently in
 * web/frontend/e2e/map-lens-cycling.spec.ts, reproduced here against the
 * cockpit's own deck.gl instance): a `pageerror` reading
 * `maxTextureDimension2D` off `undefined` occasionally fires from
 * luma.gl's device-capability query under headless/software-rendered
 * (SwiftShader) Chromium when deck.gl rewrites its fill-color GPU buffer
 * several times in quick succession. Filtered by exact message match so
 * any OTHER uncaught error still fails the test.
 */
const KNOWN_SANDBOX_WEBGL_ERROR =
  "Cannot read properties of undefined (reading 'maxTextureDimension2D')";

function unexpectedErrors(pageErrors: string[]): string[] {
  return pageErrors.filter((e) => e !== KNOWN_SANDBOX_WEBGL_ERROR);
}

async function mockRoutes(page: import("@playwright/test").Page, mapData: unknown): Promise<void> {
  await page.route("**/accounts/whoami/", (r) =>
    r.fulfill(ok({ is_authenticated: true, username: "lens-smoke" })),
  );
  await page.route("**/api/games/*/state/", (r) => r.fulfill(ok(SNAPSHOT)));
  await page.route("**/api/games/*/summary/", (r) => r.fulfill(ok(SUMMARY)));
  await page.route("**/api/games/*/communities/", (r) => r.fulfill(ok(COMMUNITIES)));
  await page.route("**/api/games/*/map/**", (r) => r.fulfill(ok(mapData)));
  await page.route("**/api/games/*/timeseries/", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(TIMESERIES) }),
  );
}

test.describe("Map lens cycling (backend-free, spec-110 B6/spec-113 Lane B)", () => {
  test("cycles all 12 registered lenses with no uncaught page error", async ({ page }) => {
    // 12 sequential lens switches = 12 full deck.gl attribute rebuilds — an
    // order of magnitude more GPU work than this file's other tests. Under
    // software GL (headless CI/SwiftShader) each rebuild costs seconds, so
    // this one legitimately needs Playwright's slow-test budget (3×).
    test.slow();
    await mockRoutes(page, MAP_DATA);

    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.goto("/game/lens-smoke");
    await page.evaluate(() => document.fonts.ready);

    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });
    const selector = page.getByTestId("map-mode-selector");
    await expect(selector).toBeVisible({ timeout: 10000 });

    for (const lens of LENSES) {
      const button = page.getByTestId(`lens-mode-${lens.id}`);
      await button.click();
      await expect(button).toHaveAttribute("aria-pressed", "true");

      // Legend text reflects the active lens (case-insensitive substring
      // — the exact copy lives in lib/lens.ts's MODE_LEGEND_LABELS/
      // METRIC_LABELS).
      await expect(page.getByTestId("lens-legend-label")).toContainText(lens.label);

      // Let deck.gl finish rewriting the GPU fill-color attribute buffer
      // before the next click — realistic UX cadence, not a workaround.
      await page.waitForTimeout(150);
    }

    expect(unexpectedErrors(pageErrors), `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual(
      [],
    );
  });

  test("empty-but-present balkanization block degrades without crashing", async ({ page }) => {
    const emptyBalkanization = { factions: [], sovereigns: [], territory_influence: [] };
    const emptyMapData = {
      type: "FeatureCollection",
      features: [],
      metadata: { balkanization: emptyBalkanization },
    };
    await mockRoutes(page, emptyMapData);

    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.goto("/game/lens-smoke");
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });

    // The default lens (imperial_rent) isn't balkanization-derived, so its
    // legend chip renders regardless — switch to a political-topology lens
    // to exercise DeckGLMap's showLensLegendLabel suppression, which
    // deliberately SUPPRESSES the legend chip (rather than rendering
    // "…— no data" text) for a balkanization lens with an empty-but-present
    // block — see its docstring: "Only show the legend-label chip … when
    // there's real data". The no-data signal lives in the fill color
    // (NO_DATA gray), not in this chip — assert the honest-absence
    // behavior, not fabricated "no data" copy.
    await page.getByTestId("lens-mode-stance").click();
    await expect(page.getByTestId("lens-legend-label")).toHaveCount(0);

    expect(unexpectedErrors(pageErrors), `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual(
      [],
    );
  });

  test("faction lens is a distinct, non-crashing state from the default imperial_rent lens", async ({
    page,
  }) => {
    await mockRoutes(page, MAP_DATA);

    await page.goto("/game/lens-smoke");
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });

    // Imperial Rent is the default (DESIGN_BIBLE.md §9 amendment 1) —
    // legend should read "Imperial Rent".
    await expect(page.getByTestId("lens-legend-label")).toContainText(/imperial rent/i);
    await expect(page.getByTestId(`lens-mode-imperial_rent`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    // Switching to faction lens is a distinct, non-crashing state (hull
    // suppression is verified at the unit level in mapLensLayers.test.ts —
    // this is the smoke-level confirmation the real page doesn't
    // white-screen on the transition).
    await page.getByTestId("lens-mode-faction").click();
    await expect(page.getByTestId("lens-legend-label")).toContainText(/faction/i);
  });

  test("pressing 'e' cycles the lens via the Q/E keyboard shortcut (spec-112 C5-1, retargeted spec-113 Lane B)", async ({
    page,
  }) => {
    await mockRoutes(page, MAP_DATA);

    await page.goto("/game/lens-smoke");
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });

    // Default lens is "imperial_rent" (LENS_REGISTRY[0]) — one KeyE press
    // advances to "exploitation_rate" (LENS_REGISTRY[1]).
    await page.keyboard.press("e");

    await expect(page.getByTestId("lens-mode-exploitation_rate")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
