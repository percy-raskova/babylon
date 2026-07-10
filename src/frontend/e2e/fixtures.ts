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
  process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${process.env.COCKPIT_E2E_PORT ?? "5174"}`;

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
