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
 *
 * `useLensCycleShortcut` (spec-112 C5-1) is the same shape again: Q/E cycle
 * `map.lens` backward/forward through `LENS_MODES`, wrapping at both ends.
 * Starting from a non-mode lens (`{kind:"metric"}`) is treated as being
 * "before the first mode" for E and "after the last mode" for Q, so the
 * first press always lands inside `LENS_MODES` rather than stepping past it.
 */

import { useEffect } from "react";
import { useStore } from "./index";
import { LENS_MODES, type Lens, type LensMode } from "@/lib/lens";

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

/**
 * `LENS_MODES[index]`, narrowed back to `LensMode` — `index` is always
 * produced by `cycleLensMode`'s own modulo arithmetic, so it's trivially
 * in-bounds; the `?? LENS_MODES[0]` fallback only satisfies
 * `noUncheckedIndexedAccess` (a non-literal tuple index types as
 * `LensMode | undefined`), it never actually fires.
 */
function lensModeAt(index: number): LensMode {
  return LENS_MODES[index] ?? LENS_MODES[0];
}

/**
 * Next `LensMode` one step in `direction` from `lens`, wrapping at both
 * ends of `LENS_MODES`. A lens whose `kind` isn't a mode (`{kind:"metric"}`)
 * has no position to step from — forward lands on `LENS_MODES[0]`, backward
 * on the last mode, so either key always re-enters the mode set.
 */
function cycleLensMode(lens: Lens, direction: 1 | -1): LensMode {
  const idx = lens.kind === "metric" ? -1 : LENS_MODES.indexOf(lens.kind);
  if (idx === -1) {
    return direction === 1 ? lensModeAt(0) : lensModeAt(LENS_MODES.length - 1);
  }
  const next = (idx + direction + LENS_MODES.length) % LENS_MODES.length;
  return lensModeAt(next);
}

/** Mount in the shell: Q/E cycles `map.lens` backward/forward through `LENS_MODES`. */
export function useLensCycleShortcut(gameId: string | null): void {
  useEffect(() => {
    if (!gameId) return;

    const handler = (event: KeyboardEvent): void => {
      if (event.code !== "KeyE" && event.code !== "KeyQ") return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTypingTarget(event.target)) return;

      const direction = event.code === "KeyE" ? 1 : -1;
      const { map } = useStore.getState();
      map.setLens({ kind: cycleLensMode(map.lens, direction) });
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [gameId]);
}
