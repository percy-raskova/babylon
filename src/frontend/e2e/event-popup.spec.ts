/**
 * Event popup (toast) on tick advance — spec-113 Lane G, architecture
 * §4.2, DESIGN_BIBLE §5.2's "two toast lifetimes". Live-backend spec (no
 * MSW/route-mocking harness for this: `eventsSlice.ingest` classifies the
 * REAL engine's `EventType` vocabulary via `lib/eventClassifier.ts`, and
 * whether any given tick produces an urgent (critical/notable) event is a
 * property of the deterministic simulation, not something this lane can
 * fabricate without duplicating the engine's own event timeline).
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts) against its own fresh `wayne_county` session (fixtures.ts's
 * `createWayneCountyGame` — an uncontended session per mutating spec file).
 *
 * NON-DETERMINISM NOTE: which tick first produces a critical/notable event
 * is a real simulation outcome, not a fixture this spec controls — Step is
 * driven in a bounded loop (`MAX_STEPS`, a fixed, statically-provable upper
 * bound per this repo's loop-bound rule) until `event-toasts` gets a child,
 * rather than asserting a specific tick. A run that exhausts the bound
 * without ANY urgent event across 20 ticks fails loudly with a clear
 * message — that itself would be a real finding (either the scenario's
 * event cadence changed, or `eventsSlice.ingest`'s classification broke),
 * never silently skipped.
 *
 * UNVERIFIED against a live backend (spec-113 Lane G handoff, 2026-07-11)
 * — see `real-loop.spec.ts`'s docstring for the environment blocker (no
 * live Django/Postgres in this lane, and `/game/:id` independently fails
 * to load in the current dev-worktree environment). Written strictly
 * against the real `EventToasts.tsx`/`eventsSlice.ts` contracts — Phase V
 * must run this live.
 */
import {
  expect,
  test,
  createWayneCountyGame,
  acknowledgeAutopauseIfPresent,
} from "./fixtures";

/** Hard cap on Step presses while waiting for an urgent (critical/notable) event to toast. */
const MAX_STEPS = 20;

test.describe("event popup on tick advance (cockpit, spec-113 Lane G)", () => {
  test.describe.configure({ mode: "serial" });

  test("stepping the tick eventually pops a toast for an urgent event", async ({ page }) => {
    // Live budget: each engine resolve runs 10-30s, and the bounded loop
    // below may need all MAX_STEPS of them before an urgent event fires.
    test.setTimeout(MAX_STEPS * 30_000 + 60_000);

    await page.goto("/lobby");
    const gameId = await createWayneCountyGame(page);
    expect(gameId, "session creation must return a session_id").toBeTruthy();

    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });

    // Attached, not visible: the always-mounted toast rail is an empty
    // flex container until the first toast lands, and an empty container
    // has a zero-size box (Playwright reports it hidden).
    const toastContainer = page.getByTestId("event-toasts");
    await expect(toastContainer).toBeAttached({ timeout: 15000 });

    let sawToast = false;
    for (let i = 0; i < MAX_STEPS; i++) {
      const stepButton = page.getByRole("button", { name: "Step" });
      await expect(stepButton).toBeEnabled({ timeout: 10000 });
      await Promise.all([
        page.waitForResponse(
          (r) =>
            r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
          { timeout: 30000 },
        ),
        stepButton.click(),
      ]);
      // Resolution terminates in PAUSED — or AUTOPAUSED when the tick's
      // events include a critical one (worldSlice calls time.autopause()
      // for the HOI4 pause-on-crisis behavior). Both are valid terminal
      // states; AUTOPAUSED is itself evidence an urgent event landed.
      // (Written as plain PAUSED before 40ef3d81, when the persistence
      // layer silently dropped events and autopause could never fire.)
      await expect(page.getByTestId("time-status")).toHaveText(/^(PAUSED|AUTOPAUSED)$/, {
        timeout: 15000,
      });

      const toastCount = await toastContainer.locator("[data-testid^='toast-']").count();
      if (toastCount > 0) {
        sawToast = true;
        break;
      }
    }

    expect(
      sawToast,
      `no urgent (critical/notable) event toasted across ${MAX_STEPS} ticks — either the ` +
        "scenario's event cadence changed or eventsSlice.ingest's classification broke",
    ).toBe(true);

    // A critical event also raises the CriticalEventModal (the autopause
    // alertdialog) OVER the toast rail — its full-screen backdrop
    // intercepts every toast click until acknowledged.
    await acknowledgeAutopauseIfPresent(page);

    // Whichever toast fired first, it carries the two-lifetime contract:
    // a persistent (critical) toast shows "Open Wire" + "Dismiss"; an
    // ephemeral (notable batch) toast shows only "Dismiss" (no per-event
    // Open Wire link — DESIGN_BIBLE §5.2's "critical fires on three
    // channels", notable does not).
    const firstToast = toastContainer.locator("[data-testid^='toast-']").first();
    await expect(firstToast).toBeVisible();
    // Pin the specific toast before dismissing: a live tick emits SEVERAL
    // urgent events, so `.first()` re-resolves to the NEXT toast once this
    // one is dismissed — assert on the captured id, not the live locator.
    const firstToastId = await firstToast.getAttribute("data-testid");
    const dismissButton = firstToast.locator("[data-testid^='toast-dismiss-']");
    await expect(dismissButton).toBeVisible();

    // Dismiss moves it into the recoverable tray (HOI4-style — never
    // deleted), retrievable from EventTray's "Missed" section.
    await dismissButton.click();
    await expect(toastContainer.locator(`[data-testid="${firstToastId}"]`)).toHaveCount(0);

    await expect(page.getByTestId("event-tray")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("event-tray-dismissed")).toBeVisible({ timeout: 10000 });
  });
});
