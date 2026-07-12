/**
 * Dev-mode MSW browser worker for the narration mock (Program 16 Lane N).
 *
 * No MSW dev/browser wiring existed in the app before this — `main.tsx`
 * mounts straight to `<App/>` with no worker bootstrap, and MSW was only
 * ever used in Vitest (`src/test/server.ts`, `msw/node`). This module adds
 * the minimal `msw/browser` counterpart, scoped to just the narration
 * contract endpoint, gated behind `VITE_MOCK_NARRATION=1` so it never
 * activates in a normal dev session or in production.
 *
 * **Integration note (outside this lane's ownership — `main.tsx` is not
 * an owned file):** to actually enable this in dev, add to `main.tsx`
 * (or another top-level bootstrap file) *before* the render call:
 *
 * ```ts
 * if (import.meta.env.DEV) {
 *   const { startNarrationMockWorker } = await import("@/mocks/narration/browser");
 *   await startNarrationMockWorker();
 * }
 * ```
 *
 * `startNarrationMockWorker()` itself checks `VITE_MOCK_NARRATION` and is
 * a no-op when unset — the guard above is just to keep the dynamic import
 * (and therefore `msw/browser`) out of production bundles entirely.
 *
 * Requires `public/mockServiceWorker.js` (generated via
 * `npx msw init public`, already checked in by this lane — regenerate
 * with the same command if the msw version bumps).
 */

import { setupWorker } from "msw/browser";
import { narrationHandlers } from "./handlers";

let started = false;

/**
 * Start the narration mock worker if `VITE_MOCK_NARRATION=1`. Idempotent
 * — safe to call more than once (e.g. via React StrictMode double-invoke).
 * Any other in-flight request (everything except
 * `GET /api/games/:id/narration/`) passes straight through to the real
 * backend (`onUnhandledRequest: "bypass"`) — this worker mocks ONLY the
 * narration contract, never the rest of the app.
 */
export async function startNarrationMockWorker(): Promise<void> {
  if (started) {
    return;
  }
  if (import.meta.env.VITE_MOCK_NARRATION !== "1") {
    return;
  }

  const worker = setupWorker(...narrationHandlers);
  await worker.start({ onUnhandledRequest: "bypass" });
  started = true;
}
