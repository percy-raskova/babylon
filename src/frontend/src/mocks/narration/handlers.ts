/**
 * MSW handlers for the narration contract endpoint (Program 16 Lane N).
 *
 * Serves `GET /api/games/:id/narration/?since_tick=N` against
 * `NARRATION_FIXTURE_BEATS`, honoring `since_tick` (strictly-greater-than
 * filter, matching `narrationPanel.ts`'s incremental-cursor contract).
 *
 * NOT registered in the global `src/test/handlers.ts` — that file is
 * outside this lane's ownership, and the narration endpoint doesn't exist
 * on the real backend yet. Consumers opt in per-test with
 * `server.use(...narrationHandlers)` (see `src/test/server.ts` /
 * `panelFactory.test.ts` for the established pattern), or via
 * `startNarrationMockWorker()` in dev (see `browser.ts`).
 */

import { http, HttpResponse } from "msw";
import type { NarrationFetchResult } from "@/lib/narration/client";
import { NARRATION_FIXTURE_BEATS } from "./fixtures";

/** Mutable so a test/dev session can flip the simulated narrator state. */
let simulatedStatus: NarrationFetchResult["status"] = "ready";

/** Set the status the mock endpoint reports (default `"ready"`). Test/dev use only. */
export function setSimulatedNarrationStatus(status: NarrationFetchResult["status"]): void {
  simulatedStatus = status;
}

/** Reset the mock endpoint back to its default `"ready"` status. */
export function resetSimulatedNarrationStatus(): void {
  simulatedStatus = "ready";
}

export const narrationHandlers = [
  http.get("/api/games/:id/narration/", ({ request }) => {
    if (simulatedStatus !== "ready") {
      const body: NarrationFetchResult = { status: simulatedStatus, beats: [] };
      return HttpResponse.json({ status: "ok", data: body });
    }

    const url = new URL(request.url);
    const sinceTickParam = url.searchParams.get("since_tick");
    const sinceTick = sinceTickParam !== null ? Number(sinceTickParam) : null;

    const beats =
      sinceTick !== null
        ? NARRATION_FIXTURE_BEATS.filter((b) => b.tick > sinceTick)
        : NARRATION_FIXTURE_BEATS;

    const body: NarrationFetchResult = { status: "ready", beats };
    return HttpResponse.json({ status: "ok", data: body });
  }),
];
