/**
 * End turn flow — Step + Play/Pause via TimeControls (spec-110 B6,
 * cockpit equivalent of web/frontend/e2e/end-turn-flow.spec.ts).
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts). Provisions its own fresh wayne_county session (see
 * fixtures.ts's createWayneCountyGame docstring for why every mutating
 * spec file needs an uncontended session) and drives the real
 * `timeSlice` state machine: `step` (exactly one resolve) then
 * `play`/`pause` (the serialized auto-resolve loop).
 *
 * KNOWN DEFECT (spec-110 B6, found 2026-07-09): every test here needs the
 * "chromium-authenticated" project's storageState, which the "setup"
 * project can never produce — see auth.setup.ts's docstring (Django's
 * CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS 403s any login origin but
 * 5173, including the cockpit's own 5174). Whole suite `fixme` until
 * that `web/` settings allowlist is fixed.
 */
import { expect, test, createWayneCountyGame } from "./fixtures";

let gameId = "";

test.describe("end turn -> tick resolution (cockpit, spec-110 B6)", () => {
  test.describe.configure({ mode: "serial" });

  test("provisions a fresh wayne_county session", async ({ page }) => {
    await page.goto("/lobby");
    gameId = await createWayneCountyGame(page);
    expect(gameId, "session creation must return a session_id").toBeTruthy();
  });

  test("Step resolves exactly one tick and returns to PAUSED", async ({ page }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);

    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED");

    const stepButton = page.getByRole("button", { name: "Step" });
    await expect(stepButton).toBeEnabled({ timeout: 10000 });
    const [resolveResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      stepButton.click(),
    ]);
    expect(resolveResp.status()).toBe(200);
    await expect(page.getByTestId("tick-value")).toHaveText("1", { timeout: 15000 });
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED", { timeout: 15000 });
  });

  test("Play advances the tick automatically; Pause halts the loop", async ({ page }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("tick-value")).toHaveText("1", { timeout: 15000 });
    const startTick = Number((await page.getByTestId("tick-value").textContent()) ?? "0");

    const playButton = page.getByRole("button", { name: "Play" });
    await expect(playButton).toBeEnabled({ timeout: 10000 });
    await playButton.click();
    await expect(page.getByTestId("time-status")).toHaveText(/PLAYING|RESOLVING/, {
      timeout: 5000,
    });

    // The serialized play loop only stops after its current in-flight
    // resolve settles (timeSlice.pause's docstring) — this is a real
    // stop-request racing a fast local loop, not an abort, so assert on
    // eventual PAUSED + tick progress rather than an exact tick count.
    await page.waitForTimeout(1500);
    await page.getByRole("button", { name: "Pause" }).click();
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED", { timeout: 20000 });

    const endTick = Number((await page.getByTestId("tick-value").textContent()) ?? "0");
    expect(endTick).toBeGreaterThan(startTick);
  });
});
