/**
 * Flat 9-verb grid (Constitution Article V — no invented tabs/groupings).
 * All 9 verbs have real, registered engine resolvers (AW3-R1, 2026-07-15
 * — see `DISABLED_VERBS`'s docstring), so none render disabled today. The
 * `DISABLED_VERBS` gate stays wired: a verb without a wired engine handler
 * would render disabled with an honest tooltip rather than being hidden —
 * Article V names nine verbs, and hiding one would misrepresent the
 * vocabulary.
 */

import { VERBS, DISABLED_VERBS } from "@/lib/verb-config";
import type { LiveVerbCost } from "@/lib/verbs";
import type { PlayerVerb } from "@/types/game";

interface VerbGridProps {
  selectedVerb: PlayerVerb | null;
  onSelect: (verb: PlayerVerb) => void;
  /** Live cost for the SELECTED verb only (null for the other 8 buttons —
   *  a fetch only ever runs for the currently-composed verb, see
   *  useVerbTargets.ts) — falls back to the static cost_label hint until
   *  the fetch resolves or when the verb has no parseCost. */
  liveCost: LiveVerbCost | null;
}

export function VerbGrid({ selectedVerb, onSelect, liveCost }: VerbGridProps): React.JSX.Element {
  return (
    <div className="grid grid-cols-3 gap-1.5" data-testid="verb-grid">
      {VERBS.map((v) => {
        const disabled = DISABLED_VERBS.has(v.verb);
        const active = selectedVerb === v.verb;
        const costText = active && liveCost ? liveCost.label : v.cost_label;
        return (
          <button
            key={v.verb}
            disabled={disabled}
            title={disabled ? `${v.label}: no engine handler yet` : `${v.label} — ${costText}`}
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
  );
}
