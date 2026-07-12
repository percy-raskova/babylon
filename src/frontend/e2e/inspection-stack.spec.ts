/**
 * InspectionStack progressive-disclosure smoke (spec-113 Lane G,
 * architecture.md §2, DESIGN_BIBLE.md §4) — backend-free.
 *
 * Same route-mocking technique as `briefing-map-smoke.spec.ts`/
 * `map-lens-cycling.spec.ts` (Playwright `page.route`, no live Django/
 * Postgres, no storageState — default "chromium" project), extended with
 * the InspectionStack's own entity/metric endpoints
 * (`GET /api/games/:id/hex/:h3/`, `GET /api/games/:id/explain/`) so the
 * full push -> resolve -> drill -> breadcrumb -> Escape flow exercises a
 * REAL browser end to end: `mapSlice.setSelection` -> `inspectSlice.push`
 * -> `lib/inspect/resolvers.ts` -> `InspectionCard`/`ValueRow`.
 *
 * WHY A HEX CLICK, NOT A DOM BUTTON: `DeckGLMap`'s territory-click handler
 * (`handleMapClick`, framing==="hex" only) fires from real deck.gl WebGL
 * picking — there is no DOM element per hexagon to `getByTestId` against.
 * The fixture's single territory uses a REAL h3-js cell
 * (`latLngToCell(42.5, -83.2, 7)`, computed once against the installed
 * `h3-js` and pinned as a literal below) chosen to sit exactly under
 * `DeckGLMap.tsx`'s `INITIAL_VIEW_STATE` center (-83.2, 42.5) — the point
 * that camera parks at screen-center regardless of pitch/bearing — so a
 * plain `page.mouse.click()` at the map region's bounding-box center lands
 * on the rendered hexagon. `mapSlice.framing` now defaults to `"county"`
 * (bible §9 amendment 2), so every test here first switches to `"hex"` via
 * the real `framing-hex` button (architecture §7's demoted-but-present
 * deep-zoom entry) before clicking.
 *
 * KNOWN ENVIRONMENT BLOCKER (found 2026-07-11, NOT a Lane G defect — see
 * the Lane G handoff report): in the current dev-worktree environment,
 * `/game/:id` (this spec, `briefing-map-smoke.spec.ts`, and
 * `map-lens-cycling.spec.ts` alike) fails to reach Playwright's `load`
 * state at all — `page.goto` hangs past 200s and the underlying `vite`
 * process pins a CPU core with no response, confirmed independently of
 * Playwright via bare `curl` against the dev server. Reproduced against a
 * freshly-started, otherwise-idle dev server; a `--config` run with the
 * `@tailwindcss/vite` plugin removed responded in <200ms for the same
 * routes, pointing at Tailwind's candidate/content scan as the likely
 * trigger, compounded by concurrent wave-3 lanes writing hundreds of
 * files under this exact worktree. This spec is written correctly against
 * the real component contracts below but is UNVERIFIED against a live
 * browser — Phase V must re-run it once the environment blocker clears.
 */
import { test, expect } from "./fixtures";
import { latLngToCell } from "h3-js";

const ok = (data: unknown) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({ status: "ok", data }),
});

/** Real h3-js cell under `DeckGLMap.tsx`'s fixed INITIAL_VIEW_STATE center. */
const H3 = latLngToCell(42.5, -83.2, 7);

const SNAPSHOT = {
  tick: 5,
  session_id: "inspect-smoke",
  organizations: [{ id: "o1", name: "WCLF", short_name: "WCLF", player_controlled: true }],
  territories: [
    {
      id: "t1",
      name: "Wayne",
      heat: 0.3,
      rent_level: 0.5,
      biocapacity: 0.4,
      population: 120000,
      h3_index: H3,
    },
  ],
  hyperedges: [],
  edges: [],
  events: [],
};

const SUMMARY = {
  tick: 5,
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
  ticks: [3, 4, 5],
  imperial_rent: [0.1, 0.2, 0.3],
  consciousness: [0.1, 0.1, 0.2],
  solidarity: [0.2, 0.2, 0.3],
  heat: [0.2, 0.25, 0.3],
  wealth: [0.5, 0.5, 0.6],
  biocapacity: [0.4, 0.4, 0.4],
};

/** `GET /api/games/:id/hex/:h3/` — `lib/inspect/adapters/hex.ts`'s raw shape. */
const HEX_ENTITY = {
  county_name: "Wayne County",
  population: 120000,
  habitability: 0.6,
  biocapacity: 0.4,
  heat: 0.3,
  rent_level: 0.5,
  dominant_class: "proletariat",
  // profit_rate is the one hex-scoped provenance-mirror metric
  // (lib/inspect/provenance.ts) — this is the row we drill through.
  profit_rate: 0.12,
};

/** `GET /api/games/:id/explain/?metric=profit_rate&scope=hex:<h3>` response. */
const EXPLAIN_PROFIT_RATE = {
  metric: "profit_rate",
  scope: `hex:${H3}`,
  value: 0.12,
  formula: { name: "Profit Rate", expression: "s / (c + v)", doc: "formulas/profit.py" },
  inputs: [
    { name: "s", label: "Surplus Value", value: 10, kind: "state", ref: null },
    { name: "c_plus_v", label: "Capital Advanced", value: 83.3, kind: "state", ref: null },
  ],
  constants: [],
};

async function mockRoutes(page: import("@playwright/test").Page): Promise<void> {
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
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(TIMESERIES) }),
  );
  await page.route(`**/api/games/*/hex/${H3}/`, (r) => r.fulfill(ok(HEX_ENTITY)));
  await page.route("**/api/games/*/explain/**", (r) => r.fulfill(ok(EXPLAIN_PROFIT_RATE)));
}

/** Switch to hex framing (bible §9 amendment 2 demoted it from default) and click the one rendered hex. */
async function clickTheHex(page: import("@playwright/test").Page): Promise<void> {
  await page.getByTestId("framing-hex").click();
  await expect(page.getByTestId("framing-hex")).toHaveAttribute("aria-pressed", "true");

  const mapRegion = page.getByTestId("region-map");
  const box = await mapRegion.boundingBox();
  if (!box) throw new Error("region-map has no bounding box — did the shell fail to mount?");

  // deck.gl picking is WebGL-side — there is no DOM element for Playwright
  // to auto-wait on, and under software GL the first hex render takes
  // seconds. Poll-click (fixed upper bound) until the stack mounts instead
  // of trusting one blind click against an unascertainable render state.
  const MAX_CLICK_ATTEMPTS = 15;
  for (let attempt = 0; attempt < MAX_CLICK_ATTEMPTS; attempt++) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    const mounted = await page
      .getByTestId("inspection-stack")
      .isVisible()
      .catch(() => false);
    if (mounted) return;
    await page.waitForTimeout(1000);
  }
  throw new Error(`hex click never mounted the inspection stack (${MAX_CLICK_ATTEMPTS} attempts)`);
}

test.describe("InspectionStack progressive disclosure (backend-free, spec-113 Lane G)", () => {
  test("click hex -> card appears -> explain row -> child card + breadcrumb -> Escape pops", async ({
    page,
  }) => {
    await mockRoutes(page);

    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.goto("/game/inspect-smoke");
    await page.evaluate(() => document.fonts.ready);
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });

    await clickTheHex(page);

    // Root frame: the hex's InspectionCard.
    const stack = page.getByTestId("inspection-stack");
    await expect(stack).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("inspection-card")).toBeVisible();
    await expect(page.getByTestId("inspection-card")).toContainText("Wayne County");
    // One frame deep — the breadcrumb has no earlier (clickable) entries yet.
    await expect(page.getByTestId("inspection-breadcrumb-0")).toHaveCount(0);

    // Drill: the "Profit Rate" row is explainable (lib/inspect/provenance.ts).
    const explainRow = page.getByTestId("explain-Profit Rate");
    await expect(explainRow).toBeVisible();
    await explainRow.click();

    // Child frame: the drilled metric renders its Expression row and the
    // breadcrumb shows the parent as a clickable entry at index 0. NOTE:
    // `formula-card` is InspectionCard's generic BODY renderer for every
    // resolved frame (hex included), so its count is 1 whenever any card
    // is open — the metric-only discriminator is `value-row-Expression`
    // (found live, spec-113 Phase V).
    await expect(page.getByTestId("value-row-Expression")).toContainText("s / (c + v)", {
      timeout: 10000,
    });
    await expect(page.getByTestId("inspection-breadcrumb-0")).toBeVisible();

    // Escape pops the top (metric) frame back to the root hex card.
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("inspection-card")).toContainText("Wayne County");
    await expect(page.getByTestId("value-row-Expression")).toHaveCount(0);
    await expect(page.getByTestId("inspection-breadcrumb-0")).toHaveCount(0);

    expect(pageErrors, `uncaught page errors: ${pageErrors.join(" | ")}`).toEqual([]);
  });

  test("clicking an earlier breadcrumb entry pops straight back to it", async ({ page }) => {
    await mockRoutes(page);

    await page.goto("/game/inspect-smoke");
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });
    await clickTheHex(page);

    await expect(page.getByTestId("inspection-card")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("explain-Profit Rate").click();
    // value-row-Expression is the metric-frame discriminator — see the
    // NOTE in the Escape test above (`formula-card` renders for EVERY frame).
    await expect(page.getByTestId("value-row-Expression")).toBeVisible({ timeout: 10000 });

    await page.getByTestId("inspection-breadcrumb-0").click();

    await expect(page.getByTestId("inspection-card")).toContainText("Wayne County");
    await expect(page.getByTestId("value-row-Expression")).toHaveCount(0);
  });

  test("inspection-close-all clears the whole stack", async ({ page }) => {
    await mockRoutes(page);

    await page.goto("/game/inspect-smoke");
    await expect(page.getByTestId("region-map")).toBeVisible({ timeout: 10000 });
    await clickTheHex(page);

    await expect(page.getByTestId("inspection-stack")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("inspection-close-all").click();
    await expect(page.getByTestId("inspection-stack")).toHaveCount(0);
  });
});
