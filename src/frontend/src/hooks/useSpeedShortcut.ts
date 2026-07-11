/**
 * useSpeedShortcut — number-key speed shortcuts (spec-113 architecture
 * §4.1, DESIGN_BIBLE §5.3: "1/2/3 = speed"). 1 -> 1x, 2 -> 2x, 3 -> 5x
 * (there are only three selectable speeds; the third key maps to the
 * fastest one).
 *
 * Deliberately separate from `store/orchestrator.ts`'s
 * `useSpacebarShortcut` (Lane B's file, not touched here) even though both
 * are `keydown` listeners: spacebar's "pause/last-speed" toggle already
 * works with zero changes there — `toggleSpacebar` calls `time.play()`,
 * which reads `time.speed` fresh at its own delay-injection point — so
 * this hook only ever owns the three number keys.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import type { TimeSpeed } from "@/store/slices/timeSlice";

const TEXT_INPUT_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return TEXT_INPUT_TAGS.has(target.tagName) || target.isContentEditable;
}

const KEY_TO_SPEED: Record<string, TimeSpeed> = { "1": 1, "2": 2, "3": 5 };

/** Mount once (from `SpeedControls`): keys 1/2/3 set the auto-resolve speed. */
export function useSpeedShortcut(): void {
  useEffect(() => {
    const handler = (event: KeyboardEvent): void => {
      if (isTypingTarget(event.target)) return;
      const speed = KEY_TO_SPEED[event.key];
      if (speed === undefined) return;
      event.preventDefault();
      useStore.getState().time.setSpeed(speed);
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}
