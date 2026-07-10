/**
 * Observatory route — dev-facing debug dashboard over the simulation
 * database (spec-096/spec-099/spec-111). Lazy-loaded so it adds no weight
 * to the main game bundle; the page itself probes `/api/observatory/status/`
 * and renders an honest "disabled/unavailable" state (Constitution III.11)
 * when `OBSERVATORY_ENABLED` is off or the simulation database is absent.
 *
 * This module is deliberately self-contained (no App.tsx/routes/* edits —
 * route-registration discipline for this wave). To wire it in, the caller
 * adds exactly one route:
 *
 * ```tsx
 * import { ObservatoryRoute } from "@/observatory/ObservatoryRoute";
 * <Route path="/observatory/*" element={<ObservatoryRoute />} />
 * ```
 */

import { lazy, Suspense } from "react";

const ObservatoryPage = lazy(() => import("./ObservatoryPage"));

export function ObservatoryRoute(): React.JSX.Element {
  return (
    <Suspense fallback={null}>
      <ObservatoryPage />
    </Suspense>
  );
}

export default ObservatoryRoute;
