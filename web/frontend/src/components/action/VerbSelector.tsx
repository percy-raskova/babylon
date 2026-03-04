/**
 * 3x3 verb grid — Constitution Article V's 9-verb vocabulary.
 *
 * Columns: BUILD ORG | PROJECT PWR | MANAGE RES
 * Each cell shows verb name, AP cost (if known), and description.
 * Verbs exceeding available AP are dimmed but still clickable
 * (Constitution I.11: all verbs always available).
 */

import type { PlayerVerb, VerbCategory } from "@/types/game";

/** Metadata for a single verb cell. */
interface VerbDef {
  verb: PlayerVerb;
  label: string;
  description: string;
  category: VerbCategory;
}

/** The 3x3 grid arranged by column (category), 3 verbs each. */
const VERB_GRID: { category: VerbCategory; label: string; verbs: VerbDef[] }[] = [
  {
    category: "build",
    label: "Build Org",
    verbs: [
      { verb: "educate", label: "Educate", description: "Raise consciousness", category: "build" },
      {
        verb: "reproduce",
        label: "Reproduce",
        description: "Grow membership",
        category: "build",
      },
      {
        verb: "investigate",
        label: "Investigate",
        description: "Gather intelligence",
        category: "build",
      },
    ],
  },
  {
    category: "project",
    label: "Project Pwr",
    verbs: [
      { verb: "attack", label: "Attack", description: "Direct action", category: "project" },
      { verb: "mobilize", label: "Mobilize", description: "Mass action", category: "project" },
      { verb: "campaign", label: "Campaign", description: "Public pressure", category: "project" },
    ],
  },
  {
    category: "manage",
    label: "Manage Res",
    verbs: [
      { verb: "aid", label: "Aid", description: "Transfer resources", category: "manage" },
      { verb: "move", label: "Move", description: "Relocate forces", category: "manage" },
      {
        verb: "negotiate",
        label: "Negotiate",
        description: "Diplomatic outreach",
        category: "manage",
      },
    ],
  },
];

const CATEGORY_COLORS: Record<VerbCategory, string> = {
  build: "text-royal-blue",
  project: "text-crimson",
  manage: "text-data-green",
};

const CATEGORY_BORDER: Record<VerbCategory, string> = {
  build: "border-royal-blue",
  project: "border-crimson",
  manage: "border-data-green",
};

interface VerbSelectorProps {
  selectedVerb: PlayerVerb | null;
  onSelect: (verb: PlayerVerb) => void;
  /** Map of verb → AP cost for the current org (if available). */
  verbCosts?: Partial<Record<PlayerVerb, number>>;
  /** Available AP for the current org. */
  availableAP?: number;
}

export function VerbSelector({
  selectedVerb,
  onSelect,
  verbCosts,
  availableAP,
}: VerbSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-1">
      {/* Column headers */}
      {VERB_GRID.map((col) => (
        <div
          key={col.category}
          className={`border-b pb-1 text-center text-[9px] font-bold uppercase tracking-widest ${CATEGORY_COLORS[col.category]} ${CATEGORY_BORDER[col.category]}`}
        >
          {col.label}
        </div>
      ))}

      {/* Verb cells — iterate row-first across columns */}
      {[0, 1, 2].map((row) =>
        VERB_GRID.map((col) => {
          const def = col.verbs[row];
          if (!def) {
            return null;
          }
          const cost = verbCosts?.[def.verb];
          const overBudget = cost !== undefined && availableAP !== undefined && cost > availableAP;
          const isSelected = selectedVerb === def.verb;

          return (
            <button
              key={def.verb}
              onClick={() => onSelect(def.verb)}
              title={def.description}
              className={`flex flex-col rounded border px-2 py-1.5 text-left transition-colors ${
                isSelected
                  ? `${CATEGORY_BORDER[def.category]} bg-dark-metal`
                  : "border-soot hover:border-wet-concrete"
              } ${overBudget ? "opacity-50" : ""}`}
            >
              <span
                className={`text-[11px] font-semibold ${
                  isSelected ? CATEGORY_COLORS[def.category] : "text-bone"
                }`}
              >
                {def.label}
              </span>
              <span className="text-[9px] text-ash">{def.description}</span>
              {cost !== undefined && (
                <span
                  className={`mt-0.5 font-mono text-[9px] ${
                    overBudget ? "text-phosphor-red" : "text-gold"
                  }`}
                >
                  {cost} AP
                </span>
              )}
            </button>
          );
        }),
      )}
    </div>
  );
}
