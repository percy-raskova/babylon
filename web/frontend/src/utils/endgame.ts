/**
 * Endgame detection utility — checks a game snapshot for terminal conditions.
 */

import type { EndgameData, GameSnapshot } from "@/types/game";

/** Endgame event types that trigger the notification. */
const ENDGAME_EVENTS = new Set([
  "REVOLUTIONARY_VICTORY",
  "ECOLOGICAL_COLLAPSE",
  "FASCIST_CONSOLIDATION",
]);

/**
 * Check a snapshot for endgame conditions.
 *
 * Returns EndgameData if a terminal event is found, null otherwise.
 */
export function detectEndgame(snapshot: GameSnapshot | null): EndgameData | null {
  if (!snapshot) return null;

  // Prefer explicit endgame field from resolve response
  if (snapshot.endgame) return snapshot.endgame;

  // Fallback: scan events for endgame event types
  const endgameEvent = snapshot.events.find((e) => ENDGAME_EVENTS.has(e.type));
  if (!endgameEvent) return null;

  return {
    outcome: endgameEvent.type as EndgameData["outcome"],
    tick: endgameEvent.tick,
    summary: (endgameEvent.data?.summary as string) ?? "",
  };
}
