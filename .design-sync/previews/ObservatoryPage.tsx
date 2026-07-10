/**
 * ObservatoryPage preview — the page shell itself: zero props, self-fetches
 * `fetchStatus()`/`fetchSessions()` on mount (`./api`, a direct `fetch()`;
 * no store), gated behind the `OBSERVATORY_ENABLED` flag probe. The
 * design-sync bundle deliberately never mounts MSW or a router (see
 * design-sync.entry.tsx), so `/api/observatory/status/` 404s against the
 * preview's static file server every time.
 *
 * With no props and no store seam, this is the ONLY statically-reachable
 * composition — and it's provably the only one, not just the one that
 * happened to get captured: package-capture's `page.goto` only resolves
 * past Playwright's `networkidle` wait, which by definition cannot fire
 * until the page's one in-flight fetch (the sole network activity) has
 * already settled — so the transient "Connecting to the simulation
 * database…" state can never survive to a screenshot either. `loadState`
 * has already flipped to "unavailable" before any capture can happen. This
 * IS the honest III.11 disabled-surface, and it happens to be the real
 * copy this component ships when `OBSERVATORY_ENABLED` is off. The
 * session-list and series/diagnostics-detail states are unreachable here —
 * see learnings.
 */
import { ObservatoryPage } from "babylon-cockpit";

export function Unavailable() {
  return (
    <div className="bg-void">
      <ObservatoryPage />
    </div>
  );
}
