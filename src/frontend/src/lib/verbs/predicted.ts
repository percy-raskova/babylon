/**
 * Predicted-effect evaluation for the pre-commit delta arrows
 * (spec-113 Lane DELTA; vision doc: verbs show "live cost and predicted
 * delta arrows BEFORE you commit").
 *
 * Pure function — no React, no store. `VerbForm` calls it on every
 * render and shows an arrow chip only when it returns a delta; every
 * null branch here is an honest-null contract (Constitution III.11):
 * no selector, no snapshot, no composable target, or a zero/non-finite
 * value all render NOTHING rather than filler.
 *
 * Scope contract: the selector's declared `scopeKind` is applied to the
 * SELECTED TARGET (`this = { kind: scopeKind, id: targetId }`); a
 * `"global"` selector evaluates with `this: null` once the verb is
 * composable (target chosen, or none required). Zero deltas render no
 * arrow — the same convention `bbl/Sparkline.tsx` uses for its trailing
 * delta indicator.
 */

import type { GameSnapshot } from "@/types/game";
import type { Scope, ScopeEntity } from "@/lib/selectors/types";
import type { VerbConfig } from "./types";

/** A renderable predicted delta: direction, metric label, raw value. */
export interface PredictedDelta {
  /** Arrow direction — "up" (▲, gold) or "down" (▼, crimson). */
  direction: "up" | "down";
  /** Metric name shown next to the arrow (the selector's label). */
  label: string;
  /** The raw signed delta the selector predicted. */
  value: number;
}

/**
 * Evaluate a verb's `predictedEffect` for the current composition state.
 *
 * Returns `null` whenever no honest arrow can be shown: the config has
 * no selector, no snapshot is loaded, the required target is not yet
 * selected, a non-global selector has no target to scope to, or the
 * evaluated delta is zero or non-finite.
 */
export function evaluatePredictedEffect(
  config: VerbConfig,
  snapshot: GameSnapshot | null,
  targetId: string | null,
): PredictedDelta | null {
  const effect = config.predictedEffect;
  if (!effect || !snapshot) return null;

  const targetRequired = config.targetRequired ?? true;
  if (targetRequired && !targetId) return null;

  let focus: ScopeEntity | null = null;
  if (effect.scopeKind !== "global") {
    if (!targetId) return null;
    focus = { kind: effect.scopeKind, id: targetId };
  }

  const scope: Scope = { snapshot, this: focus };
  const value = effect.evaluate(scope);
  if (!Number.isFinite(value) || value === 0) return null;

  return { direction: value > 0 ? "up" : "down", label: effect.label, value };
}
