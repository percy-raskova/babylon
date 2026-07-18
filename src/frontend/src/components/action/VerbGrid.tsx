/**
 * Flat 9-verb grid (Constitution Article V — no invented tabs/groupings).
 * Verbs are NEVER hidden, only disabled with an honest reason:
 *  - `DISABLED_VERBS` (static): a verb shipped without an engine handler
 *    (empty today — AW3-R1).
 *  - `eligibility` (dynamic, spec-116 FR-4.8): a verb whose target
 *    predicate is empty right now renders disabled, with the backend's
 *    reason + remedy visible below the grid — the same predicates that
 *    would otherwise produce a dead-end "No eligible targets." click.
 * HONEST-NULL: while `eligibility` is null (fetch unresolved or failed)
 * every verb renders enabled exactly as before — a fabricated disabled
 * state would be a phantom (Constitution III.11).
 */

import { VERBS, DISABLED_VERBS } from "@/lib/verb-config";
import type { LiveVerbCost } from "@/lib/verbs";
import type { PlayerVerb, VerbEligibilityEntry } from "@/types/game";
import type { V2Verb } from "@/types/v2-types";
import type { VerbEligibilityMap } from "./useVerbEligibility";

/** Compose a verb button's title — factored out of the nested
 *  static/dynamic-disabled/enabled branches to keep them flat (no nested
 *  ternary). */
function verbButtonTitle(
  v: V2Verb,
  staticDisabled: boolean,
  dyn: VerbEligibilityEntry | undefined,
  costText: string,
): string {
  if (staticDisabled) {
    return `${v.label}: no engine handler yet`;
  }
  if (dyn?.eligible === false) {
    const copy = [dyn.reason, dyn.remedy].filter(Boolean).join(" ");
    return `${v.label} — no eligible targets yet: ${copy}`;
  }
  return `${v.label} — ${costText}`;
}

interface VerbGridProps {
  selectedVerb: PlayerVerb | null;
  onSelect: (verb: PlayerVerb) => void;
  /** Live cost for the SELECTED verb only (null for the other 8 buttons —
   *  a fetch only ever runs for the currently-composed verb, see
   *  useVerbTargets.ts) — falls back to the static cost_label hint until
   *  the fetch resolves or when the verb has no parseCost. */
  liveCost: LiveVerbCost | null;
  /** Per-verb dynamic eligibility keyed by verb; null while unresolved. */
  eligibility: VerbEligibilityMap | null;
}

export function VerbGrid({
  selectedVerb,
  onSelect,
  liveCost,
  eligibility,
}: VerbGridProps): React.JSX.Element {
  const ineligible = VERBS.flatMap((v) => {
    const dyn = eligibility?.[v.verb];
    return dyn && dyn.eligible === false
      ? [{ verb: v.verb, label: v.label, reason: dyn.reason, remedy: dyn.remedy }]
      : [];
  });

  return (
    <div className="flex flex-col gap-1">
      <div className="grid grid-cols-3 gap-1.5" data-testid="verb-grid">
        {VERBS.map((v) => {
          const staticDisabled = DISABLED_VERBS.has(v.verb);
          const dyn = eligibility?.[v.verb];
          const dynDisabled = dyn?.eligible === false;
          const disabled = staticDisabled || dynDisabled;
          const active = selectedVerb === v.verb;
          const costText = active && liveCost ? liveCost.label : v.cost_label;
          const title = verbButtonTitle(v, staticDisabled, dyn, costText);
          return (
            <button
              key={v.verb}
              disabled={disabled}
              title={title}
              onClick={() => onSelect(v.verb as PlayerVerb)}
              className={`flex flex-col items-center gap-0.5 rounded border p-2 text-center disabled:cursor-not-allowed disabled:opacity-40 ${
                active
                  ? "border-spire bg-spire/10 text-spire"
                  : "border-rebar text-fog hover:border-wet-steel"
              }`}
            >
              <span className="text-base">{v.glyph}</span>
              <span className="text-[9px] uppercase tracking-widest">{v.label}</span>
            </button>
          );
        })}
      </div>
      {ineligible.length > 0 && (
        <ul data-testid="verb-ineligible-reasons" className="flex flex-col gap-0.5">
          {ineligible.map((row) => (
            <li key={row.verb} className="text-[10px] italic text-shroud">
              <span className="font-mono not-italic uppercase tracking-widest">{row.label}</span> —
              no eligible targets yet: {[row.reason, row.remedy].filter(Boolean).join(" ")}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
