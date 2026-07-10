/**
 * Real core-loop gate for the cockpit (spec-110 B6 — the Phase-B exit
 * measurement). Mirrors web/frontend/e2e/real-loop.spec.ts's shape:
 * login → lobby → create a fresh wayne_county operation → cockpit shell
 * renders (map/outliner/dock/statusbar/bottomstrip) → submit a verb via
 * the ActionComposer → Step resolves the tick → StatusBar tick advances
 * → the Events tab reflects the new tick.
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts). Requires the live stack: Django `:8000`
 * (RUN_MAIN=true, native `:5432` web DB) + the cockpit dev server.
 *
 * Tests share the session created in the second test and mutate it in
 * order (test.describe.configure({ mode: "serial" })) — game_turn
 * enforces one queued action per (session, tick, org), so replaying a
 * submit against a reused session collides with that unique constraint;
 * a session created fresh by this spec avoids that.
 *
 * KNOWN DEFECT (spec-110 B6, found 2026-07-09): every test here needs the
 * "chromium-authenticated" project's storageState, which the "setup"
 * project can never produce — see auth.setup.ts's docstring (Django's
 * CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS 403s any login origin but
 * 5173, including the cockpit's own 5174). Whole suite `fixme` until
 * that `web/` settings allowlist is fixed.
 */
import { expect, test } from "./fixtures";

/** Session id created by the "creating a wayne_county operation" test. */
let gameId = "";

test.describe.fixme("real core loop (cockpit, spec-110 B6)", () => {
  test.describe.configure({ mode: "serial" });

  test("lobby renders for the pre-authenticated session", async ({ page }) => {
    await page.goto("/lobby");
    await expect(page.getByText("New Operation")).toBeVisible({ timeout: 10000 });
  });

  test("creating a wayne_county operation provisions a fresh session", async ({ page }) => {
    await page.goto("/lobby");
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

    // The UI hands off to the cockpit shell for the new session.
    await expect(page).toHaveURL(new RegExp(`/game/${gameId}`), { timeout: 15000 });
  });

  test("cockpit shell renders all five regions with the fresh session at tick 0", async ({
    page,
  }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);

    await expect(page.getByTestId("region-statusbar")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("region-outliner")).toBeVisible();
    await expect(page.getByTestId("region-map")).toBeVisible();
    await expect(page.getByTestId("region-dock")).toBeVisible();
    await expect(page.getByTestId("region-bottomstrip")).toBeVisible();

    // Map lens selector + at least the map mount confirm DeckGLMap itself
    // rendered (not just the "No world state loaded yet." placeholder).
    await expect(page.getByTestId("map-mode-selector")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 10000 });
  });

  test("campaign verb submits through the ActionComposer's live pipeline", async ({ page }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);

    await expect(page.getByTestId("action-composer")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("No player-controlled organizations this session.")).toHaveCount(0);

    const verbGrid = page.getByTestId("verb-grid");
    await verbGrid.getByRole("button", { name: /campaign/i }).click();

    // Campaign's targets are snapshot-sourced (territories + hyperedges,
    // no fixture data) — the seeded wayne_county session has 81
    // territories, so the picker is never empty.
    const targetPicker = page.getByTestId("target-picker");
    await expect(targetPicker).toBeVisible({ timeout: 10000 });
    await targetPicker.getByRole("button").first().click();

    const submitButton = page.getByRole("button", { name: /submit campaign/i });
    await expect(submitButton).toBeEnabled({ timeout: 10000 });
    const [submitResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes(`/api/games/${gameId}/actions/campaign/`) &&
          r.request().method() === "POST",
        { timeout: 20000 },
      ),
      submitButton.click(),
    ]);
    expect(submitResp.status()).toBe(201);
    await expect(page.getByTestId("pending-actions")).toBeVisible({ timeout: 10000 });
  });

  test("Step resolves the tick and the StatusBar reflects it live", async ({ page }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });

    const stepButton = page.getByRole("button", { name: "Step" });
    await expect(stepButton).toBeEnabled({ timeout: 10000 });
    const [resolveResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      stepButton.click(),
    ]);
    expect(resolveResp.status(), "resolve endpoint must not error").toBe(200);
    await expect(page.getByTestId("tick-value")).toHaveText("1", { timeout: 15000 });
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED");
  });

  test("Events tab shows the resolved tick's classified events or the honest empty state", async ({
    page,
  }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("region-bottomstrip")).toBeVisible({ timeout: 15000 });

    // Bottom strip defaults to the Time Series tab (uiSlice.activeDockTab)
    // — switch to Events before asserting the feed is visible.
    await page.getByRole("button", { name: "Events" }).click();
    const feed = page.getByTestId("events-feed");
    await expect(feed).toBeVisible({ timeout: 10000 });
    // Never fabricated content (Constitution III.11): the feed renders
    // either at least one classified event or the honest "No events this
    // tick." copy — either way it must not be blank.
    await expect(feed).not.toBeEmpty({ timeout: 5000 });
  });
});
