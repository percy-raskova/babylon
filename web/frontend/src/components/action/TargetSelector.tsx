/**
 * Target selector — filtered list of valid targets for the selected verb.
 *
 * Targets can also be set by clicking the map or graph (via uiStore),
 * which is handled by the parent ActionComposer.
 */

import { useMemo } from "react";
import type { GameSnapshot, PlayerVerb } from "@/types/game";

/** Which node types each verb can target (Spec 052 — no entities). */
const VERB_TARGET_TYPES: Record<
  PlayerVerb,
  ("hyperedge" | "territory" | "organization" | "self")[]
> = {
  educate: ["hyperedge"],
  reproduce: ["self"],
  investigate: ["organization", "territory"],
  attack: ["organization"],
  mobilize: ["territory"],
  campaign: ["territory"],
  aid: ["organization"],
  move: ["territory"],
  negotiate: ["organization"],
};

interface TargetSelectorProps {
  snapshot: GameSnapshot;
  verb: PlayerVerb;
  selectedTarget: string | null;
  onSelect: (targetId: string | null) => void;
}

interface TargetOption {
  id: string;
  name: string;
  type: string;
}

export function TargetSelector({ snapshot, verb, selectedTarget, onSelect }: TargetSelectorProps) {
  const targetTypes = VERB_TARGET_TYPES[verb];

  const targets = useMemo(() => {
    const result: TargetOption[] = [];

    if (targetTypes.includes("self")) {
      return []; // Self-targeted verbs have no target
    }

    if (targetTypes.includes("hyperedge")) {
      for (const hx of snapshot.hyperedges) {
        result.push({ id: hx.id, name: hx.label, type: "hyperedge" });
      }
    }
    if (targetTypes.includes("territory")) {
      for (const t of snapshot.territories) {
        result.push({ id: t.id, name: t.name, type: "territory" });
      }
    }
    if (targetTypes.includes("organization")) {
      for (const o of snapshot.organizations) {
        result.push({ id: o.id, name: o.name, type: "organization" });
      }
    }

    return result;
  }, [snapshot, targetTypes]);

  // Self-targeted verbs
  if (targetTypes.includes("self")) {
    return (
      <div className="rounded border border-soot px-3 py-2 text-[11px] text-ash">
        Self-targeted — no target needed
      </div>
    );
  }

  if (targets.length === 0) {
    return (
      <div className="rounded border border-soot px-3 py-2 text-[11px] text-ash">
        No valid targets available
      </div>
    );
  }

  const TYPE_COLORS: Record<string, string> = {
    hyperedge: "text-royal-blue",
    territory: "text-gold",
    organization: "text-grow-purple",
  };

  return (
    <div className="flex max-h-[160px] flex-col gap-0.5 overflow-auto">
      {targets.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(selectedTarget === t.id ? null : t.id)}
          className={`flex items-center justify-between rounded border px-2 py-1 text-left text-[11px] transition-colors ${
            selectedTarget === t.id
              ? "border-gold bg-dark-metal"
              : "border-soot hover:border-wet-concrete"
          }`}
        >
          <span className={selectedTarget === t.id ? "font-semibold text-bone" : "text-bone"}>
            {t.name}
          </span>
          <span
            className={`text-[9px] uppercase tracking-wider ${TYPE_COLORS[t.type] ?? "text-ash"}`}
          >
            {t.type}
          </span>
        </button>
      ))}
    </div>
  );
}
