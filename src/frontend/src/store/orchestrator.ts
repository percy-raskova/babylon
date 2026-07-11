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
 * `useLensCycleShortcut` (spec-112 C5-1, retargeted spec-113 Lane B/bible
 * §9.5's "Q/E cycles (existing)"): Q/E cycle `map.lens` backward/forward
 * through `LENS_REGISTRY`'s declaration order (`@/lib/lenses/registry`)
 * instead of the narrower 5-entry `LENS_MODES` tuple — every registered
 * lens (imperial_rent, exploitation_rate, heat, solidarity_index, stance,
 * faction, collapse, class_composition, habitability) is reachable by
 * keyboard, not just the spec-093 political-topology 5. Starting from a
 * lens with no registry entry (e.g. an unregistered `{kind:"metric"}`) is
 * treated as being "before the first entry" for E and "after the last
 * entry" for Q, so the first press always lands inside the registry rather
 * than stepping past it — same edge-case contract as the old LENS_MODES
 * version, just against the wider set.
 */

import { useEffect } from "react";
import { useStore } from "./index";
import { lensKey, type Lens } from "@/lib/lens";
import { LENS_REGISTRY } from "@/lib/lenses/registry";

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
 * `LENS_REGISTRY[index].toLens()` — `index` is always produced by
 * `cycleLens`'s own modulo arithmetic, so it's trivially in-bounds; the
 * `?? LENS_REGISTRY[0]` fallback only satisfies `noUncheckedIndexedAccess`
 * (a non-literal array index types as `MapLensDef | undefined`), it never
 * actually fires.
 */
function registryLensAt(index: number): Lens {
  const def = LENS_REGISTRY[index] ?? LENS_REGISTRY[0];
  if (!def) throw new Error("lib/lenses/registry.ts: LENS_REGISTRY must not be empty");
  return def.toLens();
}

/**
 * Next `Lens` one step in `direction` from `lens`, wrapping at both ends of
 * `LENS_REGISTRY`. A lens with no registry entry (identity compared via
 * `lensKey`) has no position to step from — forward lands on
 * `LENS_REGISTRY[0]`, backward on the last entry, so either key always
 * re-enters the registered set.
 */
function cycleLens(lens: Lens, direction: 1 | -1): Lens {
  const currentKey = lensKey(lens);
  const idx = LENS_REGISTRY.findIndex((def) => lensKey(def.toLens()) === currentKey);
  if (idx === -1) {
    return direction === 1 ? registryLensAt(0) : registryLensAt(LENS_REGISTRY.length - 1);
  }
  const next = (idx + direction + LENS_REGISTRY.length) % LENS_REGISTRY.length;
  return registryLensAt(next);
}

/** Mount in the shell: Q/E cycles `map.lens` backward/forward through `LENS_REGISTRY`. */
export function useLensCycleShortcut(gameId: string | null): void {
  useEffect(() => {
    if (!gameId) return;

    const handler = (event: KeyboardEvent): void => {
      if (event.code !== "KeyE" && event.code !== "KeyQ") return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTypingTarget(event.target)) return;

      const direction = event.code === "KeyE" ? 1 : -1;
      const { map } = useStore.getState();
      map.setLens(cycleLens(map.lens, direction));
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [gameId]);
}
