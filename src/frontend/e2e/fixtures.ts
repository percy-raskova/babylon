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
 * Acknowledge the CriticalEventModal if it is up. Since 40ef3d81 events
 * reach live snapshots, so loading (or stepping) a game whose current
 * tick carries a critical event AUTOPAUSES and raises the alertdialog —
 * its full-screen backdrop intercepts every pointer action until
 * acknowledged. `resume` returns the time slice to plain "paused"
 * (timeSlice.resume), so this never sets the loop playing.
 */
export async function acknowledgeAutopauseIfPresent(page: Page): Promise<void> {
  // Settle on the status text rather than probing the modal: a one-shot
  // isVisible() races the modal's mount frame (the snapshot ingest that
  // triggers autopause may still be rendering when the caller lands here).
  //
  // Bounded retry: on initial load GameRoute.fetchState and the heartbeat
  // can both run onTickAdvanced before world.lastTick is set (both see
  // prevTick===null), and time.autopause has no per-event dedup guard —
  // so a single resume can be immediately re-autopaused by the second
  // in-flight fetch. Resume until PAUSED sticks (max ATTEMPTS — a fixed,
  // statically-provable bound per this repo's loop rule). Owner-triage:
  // the store-side double-autopause-on-load is minor real UX jank.
  const status = page.getByTestId("time-status");
  const modal = page.getByTestId("critical-event-modal");
  // Dwell-confirmed with a LONG hold: worldSlice.onTickAdvanced awaits a
  // Promise.all over every mounted panel BEFORE calling time.autopause, so
  // under live load the autopause fires several seconds after the tick was
  // observed — well after a naive resume. Require PAUSED *and* the modal
  // DETACHED (the backdrop, not the status text, is what intercepts the
  // caller's next click) to HOLD across a hold window that outlasts that
  // delayed autopause; resume resets the counter each time it re-fires.
  // Once the mount fan-out drains, steady-state heartbeats re-observe the
  // same tick and skip onTickAdvanced, so it stays put. Fixed bound.
  const ATTEMPTS = 30;
  const HOLD = 8; // ~3.2s of continuous PAUSED + no modal
  let consecutivePaused = 0;
  for (let i = 0; i < ATTEMPTS; i++) {
    await expect(status).toHaveText(/^(PAUSED|AUTOPAUSED)$/, { timeout: 15000 });
    if ((await status.textContent()) === "AUTOPAUSED") {
      consecutivePaused = 0;
      await page.getByTestId("autopause-resume").click();
    } else if ((await modal.count()) === 0 && ++consecutivePaused >= HOLD) {
      return; // held clean long enough that the delayed autopause has fired.
    }
    await page.waitForTimeout(400);
  }
  await expect(status).toHaveText("PAUSED", { timeout: 5000 });
  await expect(modal).toHaveCount(0);
}
