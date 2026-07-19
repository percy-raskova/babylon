/**
 * Shared Playwright fixtures for the cockpit e2e suite (spec-110 B6, the
 * Phase-B exit gate).
 *
 * `BASE` mirrors the dev-server origin actually in effect (see
 * `playwright.config.ts`'s `baseURL`, which reads the same
 * `COCKPIT_E2E_PORT` env var) — specs need it for `page.request` calls
 * where a relative path would otherwise resolve against Playwright's own
 * process origin, not the app's.
 *
 * `login` drives the real `/login` form end-to-end (username/password
 * placeholders + the "Enter" button — `LoginRoute.tsx`) and waits for the
 * lobby's "New Operation" panel, the cockpit's equivalent of the legacy
 * `web/frontend/e2e/auth.setup.ts`'s "Your Operations" landmark. Used
 * directly by `auth.spec.ts` (which must NOT start pre-authenticated) and
 * by `auth.setup.ts` (which persists the resulting storageState for every
 * other authenticated spec via the "chromium-authenticated" project).
 *
 * `createWayneCountyGame` provisions a fresh session via the real
 * `POST /api/games/` endpoint (bypassing the lobby UI) so every
 * authenticated spec that mutates a session (submits actions, resolves
 * ticks) gets its own uncontended session — `game_turn` enforces one
 * queued action per (session, tick, org), so sharing a session across
 * spec files racing under `fullyParallel: true` would collide. Mirrors
 * `web/frontend/e2e/real-loop.spec.ts`'s `apiPost` helper.
 */
import { test as base, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

export const test = base;
export { expect };

export const BASE =
  process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${process.env.COCKPIT_E2E_PORT ?? "5173"}`;

/** Drive the real login form and wait for the lobby to render. */
export async function login(page: Page, username = "admin", password = "admin"): Promise<void> {
  await page.goto(`${BASE}/login`);
  await page.getByPlaceholder("Username").fill(username);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByText("New Operation")).toBeVisible({ timeout: 10000 });
}

/** Read the Django CSRF token from the shared browser context's cookie jar. */
export async function csrfToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  return cookies.find((c) => c.name === "csrftoken")?.value ?? "";
}

/**
 * Create a fresh `wayne_county` session via the real API (the session's
 * authenticated cookies come from the storageState already loaded into
 * `page`'s browser context — see `playwright.config.ts`'s
 * "chromium-authenticated" project). Returns the new session id, or ""
 * on failure (callers assert truthiness — a fabricated id would silently
 * mask a broken create path, Constitution III.11).
 */
export async function createWayneCountyGame(page: Page): Promise<string> {
  const res = await page.request.post(`${BASE}/api/games/`, {
    data: { scenario: "wayne_county" },
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": await csrfToken(page),
      Referer: `${BASE}/`,
    },
  });
  if (!res.ok()) return "";
  const body = (await res.json()) as { data?: { session_id?: string } };
  return body.data?.session_id ?? "";
}

/**
 * Acknowledge the CriticalEventModal if it is up. Loading (or stepping) a
 * game whose current tick carries a critical event AUTOPAUSES and raises
 * the alertdialog — its full-screen backdrop intercepts every pointer
 * action until acknowledged. `resume` returns the time slice to plain
 * "paused" (timeSlice.resume), so this never sets the loop playing.
 *
 * Since spec-116 FR-116-2 (autopause-once) the firing keys are recorded in
 * `events.acknowledgedAutopauseKeys` BEFORE the pause lands, so a second
 * in-flight fetch can never re-autopause on the same condition — a single
 * Resume sticks. The short dwell below only covers the FIRST autopause
 * landing late (worldSlice.onTickAdvanced awaits its panel fan-out before
 * pausing); it no longer guards against re-fires. Bounds are fixed
 * constants (statically provable per this repo's loop rule).
 */
export async function acknowledgeAutopauseIfPresent(page: Page): Promise<void> {
  const status = page.getByTestId("time-status");
  const modal = page.getByTestId("critical-event-modal");
  const ATTEMPTS = 6;
  const HOLD = 3; // ~1.2s of continuous PAUSED + no modal
  let consecutivePaused = 0;
  for (let i = 0; i < ATTEMPTS; i++) {
    await expect(status).toHaveText(/^(PAUSED|AUTOPAUSED)$/, { timeout: 15000 });
    if ((await status.textContent()) === "AUTOPAUSED") {
      consecutivePaused = 0;
      await page.getByTestId("autopause-resume").click();
    } else if ((await modal.count()) === 0 && ++consecutivePaused >= HOLD) {
      return; // held clean long enough that a late first autopause would have landed.
    }
    await page.waitForTimeout(400);
  }
  await expect(status).toHaveText("PAUSED", { timeout: 5000 });
  await expect(modal).toHaveCount(0);
}

/**
 * G7-crisis test-only hook (first-session.spec.ts's crisis-window test):
 * make the NEXT `POST /resolve/` this page issues carry
 * `X-Babylon-E2E-Force-Endgame: 1`. Only when the server process has ALSO
 * opted in via `BABYLON_E2E_TEST_HOOKS=1` (`web/game/engine_bridge.py`'s
 * `_e2e_test_hooks_enabled` — never set outside an e2e run) does that
 * header make the tick end the game through the exact real `EndgameEvent`
 * construction a genuine ~5200-tick horizon termination already uses
 * (`web/game/api.py`'s `resolve_tick` view reads the header;
 * `EngineBridge.resolve_tick`'s `force_endgame_test_hook` param gates the
 * real construction on it).
 *
 * `endgame_reached` is the ONLY event the frontend classifies "critical"
 * (spec-116 FR-116-2's salience re-tier — crimson reserved for the
 * endgame alone), hence the only autopause trigger; recognizing one of the
 * five endgame *patterns* only fires the non-critical `pattern_shift`
 * event. Since the fixed-horizon design never reaches the real termination
 * this early, this is the only way to exercise the autopause/
 * critical-event machinery deterministically inside a short e2e window —
 * see the crisis-window test's own docstring for evidence this was
 * checked, not assumed.
 *
 * `page.route(..., { times: 1 })` scopes the header to exactly the next
 * matching request — it can never leak into a later resolve this page
 * makes, or into any other spec file's page/session even under a full
 * parallel e2e run against a shared dev server (each spec file gets its
 * own browser context).
 */
export async function forceEndgameOnNextResolve(page: Page): Promise<void> {
  await page.route(
    "**/resolve/",
    async (route) => {
      await route.continue({
        headers: { ...route.request().headers(), "x-babylon-e2e-force-endgame": "1" },
      });
    },
    { times: 1 },
  );
}
