/**
 * Consumes a queued composer preset (Track 1 Task 7, 2026-07-18 — "no
 * fogged dead ends") — set by `actions.presetInvestigate` when a fogged
 * field's "Investigate" CTA is clicked (`InspectionCard`'s
 * `fogInvestigateSlot`). Extracted out of `ActionComposer` both to keep its
 * cyclomatic complexity under the repo's lint ceiling and because this is a
 * self-contained "sync local state from an external store value" concern.
 *
 * Deliberately does NOT call `setVerb`/`setPresetTarget` inside a
 * `useEffect` — `react-hooks/set-state-in-effect` (enabled repo-wide, see
 * `eslint.config.js`) flags exactly that. Instead this follows React's own
 * documented "adjusting state when a prop changes" idiom: compare the
 * incoming store value against the last one seen and call setState
 * conditionally IN THE RENDER BODY (not in an effect) — this is the
 * supported escape hatch, not a workaround (see
 * https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes).
 * The one genuine effect here — clearing the STORE's `preset` — is a real
 * external-system sync (`consumePreset` is not a local `useState` setter),
 * so it is not the pattern that rule forbids.
 */

import { useEffect, useState } from "react";
import { useStore } from "@/store";
import type { ActionPreset } from "@/store/slices/actionsSlice";
import type { PlayerVerb } from "@/types/game";

export interface PresetTarget {
  id: string;
  label: string;
}

export interface InvestigatePreset {
  verb: PlayerVerb | null;
  setVerb: (verb: PlayerVerb | null) => void;
  presetTarget: PresetTarget | null;
}

export function useInvestigatePreset(): InvestigatePreset {
  const preset = useStore((s) => s.actions.preset);
  const consumePreset = useStore((s) => s.actions.consumePreset);

  const [verb, setVerb] = useState<PlayerVerb | null>(null);
  const [presetTarget, setPresetTarget] = useState<PresetTarget | null>(null);
  // Deliberately NOT `useState(preset)` — that would capture whatever
  // preset is ALREADY active at mount as the baseline, so an already-queued
  // preset (exactly this hook's main use case: `ActionComposer` mounts
  // AFTER a fog card's CTA already called `presetInvestigate`) would look
  // like "nothing changed" and silently never apply. `null` is a safe fixed
  // baseline: the common "no preset queued" case starts genuinely equal to
  // it (no false trigger), while a real preset present at mount always
  // differs from it (correctly triggers once).
  const [lastPreset, setLastPreset] = useState<ActionPreset | null>(null);

  if (preset !== lastPreset) {
    setLastPreset(preset);
    if (preset) {
      setVerb(preset.verb);
      setPresetTarget({ id: preset.targetId, label: preset.targetLabel });
    }
  }

  useEffect(() => {
    if (preset) consumePreset();
  }, [preset, consumePreset]);

  // PR #211 review: the preset's target dies with the verb it was queued
  // for. `VerbForm` remounts on every verb change (keyed by org+verb) and
  // reads `initialTargetId` fresh, so a lingering presetTarget would
  // silently pre-target whatever verb the user switches to next.
  const selectVerb = (next: PlayerVerb | null): void => {
    setVerb(next);
    setPresetTarget(null);
  };

  return { verb, setVerb: selectVerb, presetTarget };
}
