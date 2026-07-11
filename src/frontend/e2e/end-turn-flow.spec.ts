/**
 * End turn flow — Step + Play/Pause via TimeControls, plus SpeedControls
 * (spec-110 B6, cockpit equivalent of web/frontend/e2e/end-turn-flow.spec.ts;
 * speed coverage added spec-113 Lane G per architecture §5's Lane G brief).
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts). Provisions its own fresh wayne_county session (see
 * fixtures.ts's createWayneCountyGame docstring for why every mutating
 * spec file needs an uncontended session) and drives the real
 * `timeSlice` state machine: `step` (exactly one resolve) then
 * `play`/`pause` (the serialized auto-resolve loop), then the speed
 * cluster (`SpeedControls.tsx`, architecture §4.1).
 *
 * SPEED TESTIDS (read from `SpeedControls.tsx`, not assumed): the three
 * selectable speeds are 1x/2x/5x, rendered as `speed-1`/`speed-2`/`speed-5`
 * (there is no "speed-3" — `useSpeedShortcut.ts`'s number-key map is
 * `{"1":1, "2":2, "3":5}`, i.e. the THIRD key maps to the fifth-multiplier
 * button, not a "speed-3" testid).
 *
 * KNOWN DEFECT (spec-110 B6, found 2026-07-09): every test here needs the
 * "chromium-authenticated" project's storageState, which the "setup"
 * project can never produce — see auth.setup.ts's docstring (Django's
 * CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS 403s any login origin but
 * 5173, including the cockpit's own 5174). Whole suite `fixme` until
 * that `web/` settings allowlist is fixed.
 *
 * UNVERIFIED against a live backend (spec-113 Lane G handoff, 2026-07-11)
 * — see `real-loop.spec.ts`'s docstring for the same environment blocker
 * (no live Django/Postgres in this lane, and `/game/:id` independently
 * fails to load in the current dev-worktree environment). Rewritten
 * strictly against the real `SpeedControls.tsx`/`useSpeedShortcut.ts`
 * contracts — Phase V must run this live.
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

  test("selecting 2x speed then Play reflects a playing state; spacebar pauses", async ({
    page,
  }) => {
    // Live budget: the PAUSED assertion below allots 45s (one in-flight
    // engine resolve) — the default 30s TEST budget would truncate it.
    // KNOWN RED (engine, not frontend): the play loop can 500 mid-run on
    // the UNKNOWN-event UniqueViolation (see HANDOFF-PHASE-V.md owner
    // items) — status then honestly shows ERROR and this test fails.
    test.setTimeout(120_000);
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED", { timeout: 15000 });

    // Speed is valid to set in any status (SpeedControls.tsx's docstring:
    // "setSpeed is valid in any status ... stay live even mid-resolve") —
    // set it before Play so the auto-resolve loop reads it at its own
    // delay-injection point (timeSlice's settleAfterResolve).
    const speed2 = page.getByTestId("speed-2");
    await speed2.click();
    await expect(speed2).toHaveAttribute("aria-pressed", "true");

    const playButton = page.getByRole("button", { name: "Play" });
    await expect(playButton).toBeEnabled({ timeout: 10000 });
    await playButton.click();
    await expect(page.getByTestId("time-status")).toHaveText(/PLAYING|RESOLVING/, {
      timeout: 5000,
    });

    // Spacebar toggles play/pause via time.toggleSpacebar (store/
    // orchestrator.ts's useSpacebarShortcut) — same stop-request semantics
    // as clicking Pause (the serialized loop only stops once its current
    // in-flight resolve settles), so assert eventual PAUSED, not instant.
    // Budget: one full live engine tick can run 20-30s (the Step test above
    // allots 30s for a single resolve) — 45s covers a resolve that had just
    // started when Space landed, without masking a stuck loop.
    await page.keyboard.press("Space");
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED", { timeout: 45000 });
  });
});
