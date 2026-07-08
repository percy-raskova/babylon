/**
 * Real core-loop gate (remediation C.5): login → seeded game visible →
 * create a fresh wayne_county operation → real map features → live verb
 * pipeline → UI submit → end turn → tick advances → results + event log.
 *
 * Unlike verb-submit.spec.ts (render-only) this spec drives the FULL
 * create→submit→resolve→results path against a live Postgres-backed
 * EngineBridge. Requires SPEC061_TEST_SESSION_ID + a running dev server
 * (Django :8000 + Vite :5173) and the seeded admin/admin user
 * (seed_initial_game). Skipped automatically otherwise.
 *
 * The mutating tests run against a session CREATED by this spec (not the
 * shared seeded one) because game_turn enforces one queued action per
 * (session, tick, org) — replaying a submit against a reused session
 * collides with that unique constraint. A fresh session per run keeps
 * the suite re-runnable and additionally gates the create_game →
 * hex_latest projection path (P0 #7).
 *
 * Owner setup:
 *   1. mise run db:up && mise run web:migrate
 *   2. RUN_MAIN=true poetry run python web/manage.py seed_initial_game --scenario wayne_county
 *   3. mise run web:dev
 *   4. SPEC061_TEST_SESSION_ID=<printed id> npx playwright test real-loop
 *
 * Verified seed facts this spec is calibrated against (wayne_county,
 * rng_seed 0, tick 0): 81 hex territories, 1 player org (cadre_labor
 * 1.0 < educate cost), zero eligible educate communities, campaign
 * affordable against any snapshot territory. The educate tests assert
 * the LIVE pipeline contract (P0 #4 + 5th P0); the campaign test is the
 * genuinely completable UI write path today.
 *
 * The final end-turn test is the acceptance gate for bug #6 (tick
 * resolve 500: datetime not JSON serializable — fix/tick-resolve-datetime,
 * Phase 1.1). It is RED until that branch merges; do NOT weaken it.
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const SESSION_ID = process.env.SPEC061_TEST_SESSION_ID;
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";

/** Session id created by the "creating a wayne_county operation" test. */
let gameId = "";

/** Log in through the real login form and wait for the operations list. */
async function login(page: Page): Promise<void> {
  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder("Username").fill("admin");
  await page.getByPlaceholder("Password").fill("admin");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("Your Operations")).toBeVisible({ timeout: 10000 });
}

/** Read the Django CSRF token from the shared browser context cookies. */
async function csrfToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  const token = cookies.find((c) => c.name === "csrftoken")?.value;
  expect(token, "csrftoken cookie must exist after login").toBeTruthy();
  return token ?? "";
}

/** Session-authenticated JSON POST via the page's cookie jar. */
async function apiPost(
  page: Page,
  path: string,
  body: Record<string, unknown>,
): Promise<{ status: number; json: Record<string, unknown> }> {
  const res = await page.request.post(`${BASE}${path}`, {
    data: body,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": await csrfToken(page),
      Referer: `${BASE}/`,
    },
  });
  return { status: res.status(), json: (await res.json()) as Record<string, unknown> };
}

test.describe("real core loop (C.5 gate)", () => {
  test.skip(!SESSION_ID, "SPEC061_TEST_SESSION_ID env var required");
  // Serial: the tests share the session created in the second test and
  // the later ones mutate it in loop order.
  test.describe.configure({ mode: "serial" });

  test("login lands on the operations list showing the seeded game", async ({ page }) => {
    await login(page);
    await expect(page.getByText("New Operation")).toBeVisible();
    // The seeded wayne_county game card renders (the exact regression
    // bug #1 / snapshot_json caused: GET /api/games/ 500ing).
    await expect(page.getByText("wayne_county", { exact: true }).first()).toBeVisible();
  });

  test("creating a wayne_county operation provisions a fresh session", async ({ page }) => {
    await login(page);
    await page.locator("select").selectOption("wayne_county");

    const [createResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/api/games/") && r.request().method() === "POST",
        { timeout: 60000 },
      ),
      page.getByRole("button", { name: /new game/i }).click(),
    ]);
    expect(createResp.status()).toBe(201);
    const body = (await createResp.json()) as { data?: { session_id?: string } };
    gameId = body.data?.session_id ?? "";
    expect(gameId, "create response must carry data.session_id").toBeTruthy();

    // The UI hands off to the briefing page of the new session.
    await expect(page).toHaveURL(new RegExp(`/games/${gameId}`), { timeout: 15000 });
  });

  test("map endpoint serves real GeoJSON features for the created session", async ({ page }) => {
    // API-level gate for P0 #7 (hex projection at create_game): real
    // features, not the empty FeatureCollection the self-stubbed map
    // smokes fabricate.
    expect(gameId, "created-session test ran first").toBeTruthy();
    await login(page);

    const county = await page.request.get(`${BASE}/api/games/${gameId}/map/?zoom=county`);
    expect(county.ok()).toBe(true);
    const countyBody = (await county.json()) as { data?: { features?: unknown[] } };
    expect(countyBody.data?.features?.length ?? 0).toBeGreaterThan(0);

    const hex = await page.request.get(`${BASE}/api/games/${gameId}/map/?zoom=hex`);
    expect(hex.ok()).toBe(true);
    const hexBody = (await hex.json()) as { data?: { features?: unknown[] } };
    expect(hexBody.data?.features?.length ?? 0).toBeGreaterThan(0);
  });

  test("educate composer renders the live verb pipeline (5th P0)", async ({ page }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await login(page);

    // The composer must source targets from the live per-verb endpoint,
    // not fixtures — wait for the actual GET to fire and answer ok.
    const targetsPromise = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/games/${gameId}/actions/educate/targets/`) &&
        r.request().method() === "GET",
      { timeout: 20000 },
    );
    await page.goto(`${BASE}/games/${gameId}/actions/educate`);
    const targetsResp = await targetsPromise;
    expect(targetsResp.ok()).toBe(true);
    const targetsBody = (await targetsResp.json()) as { targets?: unknown[] };

    // Actor panel is fed by the live snapshot (no fixture orgs).
    await expect(page.getByText("Acting Org")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("No player orgs in this session.")).toHaveCount(0);

    // Target list mirrors the endpoint's answer honestly: the seeded
    // wayne_county session has no eligible educate communities at tick 0,
    // so the empty state must render — never invented fixture targets.
    const nTargets = targetsBody.targets?.length ?? 0;
    if (nTargets === 0) {
      await expect(page.getByText("No eligible targets.")).toBeVisible({ timeout: 10000 });
    } else {
      await expect(page.getByText(`Eligible Targets (${nTargets})`)).toBeVisible({
        timeout: 10000,
      });
    }
  });

  test("educate submit payload shape is accepted by the serializer (P0 #4)", async ({ page }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await login(page);

    // Resolve the live player org and a community id from the real
    // endpoints — nothing hardcoded from fixtures.
    const orgsRes = await page.request.get(
      `${BASE}/api/games/${gameId}/organizations/?player_only=true`,
    );
    expect(orgsRes.ok()).toBe(true);
    const orgs = ((await orgsRes.json()) as { data: { organizations: { id: string }[] } }).data
      .organizations;
    expect(orgs.length).toBeGreaterThan(0);
    const orgId = orgs[0].id;

    const targetsRes = await page.request.get(
      `${BASE}/api/games/${gameId}/actions/educate/targets/?org_id=${orgId}`,
    );
    expect(targetsRes.ok()).toBe(true);
    const tBody = (await targetsRes.json()) as {
      targets?: { community_id: string }[];
      unavailable_communities?: { community_id: string }[];
    };
    const communityId =
      tBody.targets?.[0]?.community_id ?? tBody.unavailable_communities?.[0]?.community_id;
    expect(communityId, "the session must expose at least one community id").toBeTruthy();

    // The exact P0 #4 regression: the old client sent {target_id} and the
    // serializer rejected it with field errors ("Validation failed").
    // The live payload shape (org_id + target_community_id + params) must
    // pass serializer validation. In the seeded scenario the org cannot
    // afford educate (1.0 < 2.0 cadre labor), so the real backend answers
    // with a clean DOMAIN rejection — never a field-validation failure.
    const { status, json } = await apiPost(page, `/api/games/${gameId}/actions/educate/`, {
      org_id: orgId,
      target_community_id: communityId,
      params: {},
    });
    expect([201, 400]).toContain(status);
    expect(json.errors, "serializer must not reject the live payload shape").toBeUndefined();
    if (status === 400) {
      expect(String(json.message)).toMatch(/Cannot afford 'educate'/);
    }
  });

  test("campaign submits through the UI without rejection", async ({ page }) => {
    // The genuinely completable UI write path in the seeded scenario:
    // campaign targets come from the snapshot (81 territories) and the
    // seeded org can afford it. Full click path: compose → queue → 201.
    expect(gameId, "created-session test ran first").toBeTruthy();
    await login(page);
    await page.goto(`${BASE}/games/${gameId}/actions/campaign`);

    const queueButton = page.getByRole("button", { name: /queue campaign/i });
    await expect(queueButton).toBeVisible({ timeout: 15000 });
    await expect(queueButton).toBeEnabled({ timeout: 15000 });

    const [submitResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes(`/api/games/${gameId}/actions/campaign/`) &&
          r.request().method() === "POST",
        { timeout: 20000 },
      ),
      queueButton.click(),
    ]);
    expect(submitResp.status()).toBe(201);
  });

  test("end turn advances the tick and records results + events", async ({ page }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await login(page);

    // Capture the tick before resolving.
    const before = await page.request.get(`${BASE}/api/games/${gameId}/state/`);
    expect(before.ok()).toBe(true);
    const tickBefore = ((await before.json()) as { tick: number }).tick;

    await page.goto(`${BASE}/games/${gameId}/orgs`);
    await expect(page.getByText(/End Turn/)).toBeVisible({ timeout: 10000 });

    const [resolveResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      page.getByText(/End Turn/).click(),
    ]);
    // Bug #6 acceptance gate: resolve must not 500 (datetime TypeError in
    // persist_tick). RED until fix/tick-resolve-datetime (Phase 1.1) merges.
    expect(resolveResp.status(), "resolve endpoint must not 500 (bug #6)").toBe(200);

    // Resolution screen, then dismiss.
    await expect(page).toHaveURL(new RegExp(`/games/${gameId}/resolution$`), {
      timeout: 20000,
    });
    await expect(page.getByText(/Resolving Tick/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Continue/)).toBeVisible({ timeout: 15000 });
    await page.getByText(/Continue/).click();

    // The tick advanced in the real backend state.
    const after = await page.request.get(`${BASE}/api/games/${gameId}/state/`);
    expect(after.ok()).toBe(true);
    const tickAfter = ((await after.json()) as { tick: number }).tick;
    expect(tickAfter).toBeGreaterThan(tickBefore);

    // Results endpoint answers for the resolved tick and the page renders.
    const results = await page.request.get(`${BASE}/api/games/${gameId}/results/${tickAfter}/`);
    expect(results.ok()).toBe(true);
    const resultsBody = (await results.json()) as { status: string; data: unknown };
    expect(resultsBody.status).toBe("ok");
    expect(Array.isArray(resultsBody.data)).toBe(true);
    await page.goto(`${BASE}/games/${gameId}/results`);
    await expect(page.getByText(/resolution summary/)).toBeVisible({ timeout: 10000 });

    // Event log renders history (or the honest empty state) without crashing.
    await page.goto(`${BASE}/games/${gameId}/log`);
    await expect(page.getByText(/Event Log/i).first()).toBeVisible({ timeout: 10000 });
    const hasEntryOrEmptyState = await page
      .getByText(/No events recorded yet|t=\d+/)
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    expect(hasEntryOrEmptyState).toBe(true);
  });
});
