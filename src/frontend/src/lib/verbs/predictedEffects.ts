/**
 * Directional predictedEffect builder for the verb registry (Program 17
 * Wave 1 item 1e).
 *
 * `evaluatePredictedEffect` (./predicted) evaluates a verb's
 * `ScriptValue` and shows a ▲/▼ chip from its sign. Every registry verb
 * wired here uses a CONSTANT `evaluate()` (`() => direction`) rather than
 * a real snapshot-field lookup — matching predicted.test.ts's own tested
 * "global scope" fixture (`evaluate: () => 0.25`, a bare constant).
 *
 * WHY a constant, not a computed value: `Scope` (lib/selectors/types.ts)
 * carries only `{snapshot, this}` — no acting-org id and no visibility
 * into the verb form's current paramFields selection (mode/scan_type/
 * proposal). The backend's real per-tick magnitude formulas branch on
 * both (tendency_modifier by acting-org consciousness_strategy; per-mode
 * branches in reproduce/attack/move/investigate/negotiate) and are not
 * reproducible from a `GameSnapshot` alone. Each verb config's own
 * comment cites the real engine resolver this directional claim is
 * grounded in (Constitution III.11 / Aleksandrov Test) and flags where
 * the constant direction is only true for the DEFAULT param state — this
 * is a directional estimate, not a computed value.
 */

import type { ScopeEntityKind, ScriptValue } from "@/lib/selectors/types";

/** Build a constant-direction predictedEffect selector for a verb config. */
export function makeDirectionalEffect(
  name: string,
  label: string,
  description: string,
  scopeKind: ScopeEntityKind,
  direction: 1 | -1,
): ScriptValue {
  return {
    name,
    label,
    description,
    scopeKind,
    evaluate: () => direction,
    breakdown: () => ({ total: direction, contributors: [] }),
  };
}
