/**
 * Fetch orchestrator — the single heartbeat that replaces 13 independent
 * 2s pollers (spec-110 B3).
 *
 * `startHeartbeat(gameId)` runs one `GET /state/` every `HEARTBEAT_MS`,
 * skipping the request entirely while the tab is hidden
 * (`document.visibilityState !== "visible"`) — no fetch happens in the
 * background, and no catch-up burst happens on refocus (the next tick of
 * the interval just fires normally). Tick-change fan-out lives in
 * `worldSlice.fetchState` (`onTickAdvanced`), not here — the heartbeat's
 * only job is deciding *when* to ask.
 *
 * `useSpacebarShortcut` is exported for the stage-2 shell to mount; it
 * wires the store-level `time.toggleSpacebar` handler to a `keydown`
 * listener, ignoring the event when focus is inside a text input (so
 * typing a space in a field doesn't toggle play/pause).
 */

import { useEffect } from "react";
import { useStore } from "./index";

export const HEARTBEAT_MS = 2000;

/** Start the visibility-gated heartbeat for `gameId`. Returns a stop function. */
export function startHeartbeat(gameId: string): () => void {
  const tick = (): void => {
    if (document.visibilityState !== "visible") return;
    useStore.getState().world.fetchState(gameId);
  };

  const interval = setInterval(tick, HEARTBEAT_MS);
  return () => clearInterval(interval);
}

const TEXT_INPUT_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return TEXT_INPUT_TAGS.has(target.tagName) || target.isContentEditable;
}

/** Mount in the shell: spacebar toggles play/pause via `time.toggleSpacebar`. */
export function useSpacebarShortcut(gameId: string | null): void {
  useEffect(() => {
    if (!gameId) return;

    const handler = (event: KeyboardEvent): void => {
      if (event.code !== "Space" || isTypingTarget(event.target)) return;
      event.preventDefault();
      useStore.getState().time.toggleSpacebar(gameId);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [gameId]);
}

/** Mount alongside `startHeartbeat` in the shell — starts/stops on gameId change. */
export function useHeartbeat(gameId: string | null): void {
  useEffect(() => {
    if (!gameId) return;
    return startHeartbeat(gameId);
  }, [gameId]);
}
