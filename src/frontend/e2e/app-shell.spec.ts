/**
 * E2E spec (spec-110 B3 stage 2) — still skipped.
 *
 * The full routes/screens now exist (`/login`, `/lobby`, `/game/:id` with
 * the five-region AppShell — see `src/App.tsx` and
 * `src/components/shell/AppShell.tsx`), and every screen is exercised by
 * component + unit tests against MSW. What is NOT trivially possible
 * without a live backend: `playwright.config.ts`'s `webServer` starts only
 * the Vite dev server, which proxies `/api`, `/accounts`, `/health` to
 * `localhost:8000` (`vite.config.ts`) — there is no Django bridge (or
 * Postgres) running in this harness, so `page.goto("/")` would 404/ECONNREFUSED
 * on the very first `/accounts/whoami/` call. Driving this spec for real
 * needs either a live `web/` bridge + Postgres stood up alongside Vite, or
 * Playwright-level `page.route()` mocking of the Django endpoints (a
 * separate, non-trivial harness investment — tracked as owner item 27 per
 * `ai-docs` memory, not scoped to this lane). Left skipped rather than
 * faked green.
 */

import { test } from "./fixtures";

test.skip("cockpit app shell loads", async ({ page }) => {
  await page.goto("/");
});
