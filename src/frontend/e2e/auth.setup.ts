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
 * web DB) + the cockpit dev server (`COCKPIT_E2E_PORT`, default 5174) +
 * the seeded admin/admin user (`web/game/management/commands/
 * seed_initial_game.py` — password == username, verified live 2026-07-09).
 *
 * KNOWN DEFECT (spec-110 B6, found + verified 2026-07-09, product not
 * test infra): `web/babylon_web/settings/development.py`'s
 * `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` only list
 * `http://localhost:5173` (the legacy web/frontend port) — not the
 * cockpit's own canonical port 5174 (ADR061 / vite.config.ts). Django's
 * CSRF middleware rejects any unsafe (POST/PUT/DELETE) request whose
 * `Origin` header doesn't match that allowlist, and the browser attaches
 * `Origin` to every such fetch even though Vite's dev proxy
 * (`changeOrigin: true`) makes it look same-origin to the app. Verified
 * this blocks EVERY real in-browser mutation through the cockpit, not
 * just login: `POST /accounts/login/`, `POST /api/games/` (create),
 * `POST /api/games/{id}/actions/{verb}/` (submit), and
 * `POST /api/games/{id}/resolve/` (step/play) all 403 — reproduced with a
 * pre-authenticated session cookie (bypassing login entirely) via a
 * scratch Playwright config against the live stack, and independently via
 * raw curl (`Origin: http://localhost:5180` -> 403 with a valid
 * csrftoken cookie + `X-CSRFToken` header on an otherwise-correct
 * request). One consequence in the UI: `LoginRoute`'s submit hangs on
 * "Authenticating…" forever, because `postForm`'s `response.json()`
 * throws on the 403 response's HTML body — an unhandled rejection that
 * never resets `submitting`. Fix is a `web/` settings change (add 5174,
 * ideally read from an env var so future ports don't repeat this), out
 * of this lane's `src/frontend/e2e/**` + `playwright.config.ts`
 * ownership — left `fixme`, not silently weakened, per Constitution
 * III.11.
 */
import { test as setup, login } from "./fixtures";

/** Where the authenticated storage state is written; consumed via `use.storageState`. */
export const AUTH_FILE = "playwright/.auth/user.json";

setup.fixme("authenticate", async ({ page }) => {
  await login(page);
  await page.context().storageState({ path: AUTH_FILE });
});
