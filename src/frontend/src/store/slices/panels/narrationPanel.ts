/**
 * Narration panel — AI-narration slot for the (currently contract-only)
 * `GET /api/games/{id}/narration/` endpoint (Program 16 Lane N; see
 * `lib/narration/client.ts` for the full request/response contract).
 *
 * Modeled on `inspectorPanel.ts`'s self-contained factory shape rather
 * than `panelFactory.createPanel<T>` directly: this panel's `fetch` needs
 * to read its OWN prior state (the highest `tick` already held) to build
 * the next `since_tick` cursor, and it distinguishes two states that
 * `Panel<T>`'s `data: T | null` can't — `status` (the domain
 * `NarrationState`: offline/pending/ready) is orthogonal to `loading`
 * (this fetch's in-flight state) and `error` (this fetch's transport
 * failure). `fetchNarration` itself never throws and degrades every
 * failure (404, 5xx, network) to `{status: "offline", beats: []}` per
 * Constitution III.11, so `error` stays `null` in practice today — it is
 * kept for shape parity with the other panels and as a documented
 * extension point if a future 4th `NarrationState` distinguishes "off"
 * from "broke".
 *
 * NOT registered in `panels/index.ts` / `store/index.ts` by this lane —
 * owner directive (2026-07-11): typed slots + mocks now, the orchestrator
 * wires this into `PanelsSlice`/`PANEL_KEYS` (or a narration-specific
 * fan-out list, since beats are cumulative/incremental unlike the other
 * tick-driven panels) in a later wave. Tests exercise `createNarrationPanel`
 * directly.
 */

import { fetchNarration } from "@/lib/narration/client";
import type { NarrationBeat, NarrationState } from "@/types/narration";

export interface NarrationPanelState {
  /** Narrator availability — distinct from `loading`/`error` (this fetch's transport state). */
  status: NarrationState;
  /** All beats received so far this session, deduped by id, ascending by tick. */
  beats: NarrationBeat[];
  loading: boolean;
  error: string | null;
  mounted: boolean;
}

export interface NarrationPanel extends NarrationPanelState {
  /** Fetch new beats since the highest tick already held. Safe to call repeatedly. */
  fetch: (gameId: string) => Promise<void>;
  /** Mark this panel on/off screen — governs tick-fan-out eligibility once wired. */
  setMounted: (mounted: boolean) => void;
}

/** Merge incoming beats into existing ones, deduped by id, sorted ascending by tick. */
function mergeBeats(existing: NarrationBeat[], incoming: NarrationBeat[]): NarrationBeat[] {
  const byId = new Map(existing.map((b) => [b.id, b]));
  for (const b of incoming) {
    byId.set(b.id, b);
  }
  return [...byId.values()].sort((a, b) => a.tick - b.tick);
}

/** Highest `tick` among held beats, or `undefined` when none are held yet. */
function highestTick(beats: NarrationBeat[]): number | undefined {
  return beats.length > 0 ? Math.max(...beats.map((b) => b.tick)) : undefined;
}

/**
 * Build one `NarrationPanel`.
 *
 * `updateSelf` splices this panel's updated state back into whatever
 * composes it (mirrors `panelFactory.createPanel`'s contract). `getSelf`
 * reads this panel's OWN current state back out — needed because `fetch`
 * must know the highest tick it already holds before building the next
 * request; `createPanel` doesn't need this because its endpoints never
 * depend on the panel's own prior data.
 */
export function createNarrationPanel(
  updateSelf: (updater: (p: NarrationPanel) => NarrationPanel) => void,
  getSelf: () => NarrationPanel,
): NarrationPanel {
  const fetch = async (gameId: string): Promise<void> => {
    updateSelf((p) => ({ ...p, loading: true, error: null }));
    const sinceTick = highestTick(getSelf().beats);
    const result = await fetchNarration(gameId, sinceTick);
    updateSelf((p) => ({
      ...p,
      status: result.status,
      beats: mergeBeats(p.beats, result.beats),
      loading: false,
      error: null,
    }));
  };

  const setMounted = (mounted: boolean): void => updateSelf((p) => ({ ...p, mounted }));

  return {
    status: "offline",
    beats: [],
    loading: false,
    error: null,
    mounted: false,
    fetch,
    setMounted,
  };
}
