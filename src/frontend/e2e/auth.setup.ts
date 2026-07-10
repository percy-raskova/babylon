/**
 * Playwright auth setup project (spec-110 B6).
 *
 * Logs in once through the real Django login form (`login()` from
 * `fixtures.ts` — same flow `auth.spec.ts` drives per-test) and persists
 * the authenticated browser storage state to disk. Spec projects with
 * `dependencies: ["setup"]` and `use.storageState: AUTH_FILE`
 * (`playwright.config.ts`'s "chromium-authenticated" project) start every
 * test already logged in, instead of landing on `/login` and false-redding.
 *
 * Requires the live stack: Django `:8000` (RUN_MAIN=true, native `:5432`
 * web DB) + the cockpit dev server (`COCKPIT_E2E_PORT`, default 5173 —
 * the canonical frontend port since the spec-112 cutover) + the seeded
 * admin/admin user (`web/game/management/commands/
 * seed_initial_game.py` — password == username, verified live 2026-07-09).
 *
 * HISTORY (spec-110 B6, resolved d5f270b2): Django's dev
 * `CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` once trusted only the
 * legacy 5173, 403-ing EVERY in-browser mutation from the cockpit's
 * then-port 5174 (login/create/submit/resolve). The allowlist now names
 * the canonical origin and `BABYLON_EXTRA_DEV_ORIGINS` (comma-separated
 * env) covers any future port, so this class of defect stays loud in
 * settings rather than silent in tests. Per Constitution
 * III.11.
 */
import { test as setup, login } from "./fixtures";

/** Where the authenticated storage state is written; consumed via `use.storageState`. */
export const AUTH_FILE = "playwright/.auth/user.json";

setup("authenticate", async ({ page }) => {
  await login(page);
  await page.context().storageState({ path: AUTH_FILE });
});
