/**
 * `org`-kind resolver adapter — `GET /api/games/:id/org/:id/`
 * (architecture.md §2.4, `EngineBridge.get_inspector_org`). Ported field
 * set from the legacy `InspectorPanel.tsx`'s `OrgFields`/
 * `ConsciousnessBreakdown` (now a `composition` row rendered by
 * `BreakdownBar`), extended with "explain" refs for the four org-scoped
 * provenance-mirror metrics when the raw payload carries a matching field.
 *
 * Program 17 Wave 1 / W1.3 adds two player-org-only sections, sourced from
 * the bridge's ``vanguard`` / ``traps`` fields (both ``null`` for non-player
 * orgs — the sections are omitted entirely, never rendered as empty
 * shells): "Vanguard Resources" (Cadre/Sympathizer Labor as [current,
 * headroom] `BreakdownBar` compositions, Reputation as a plain row — always
 * `null` today, since no `VanguardResources.from_organization` call site
 * carries it tick-to-tick yet) and "Trap Detection" (active-trap status,
 * the three trap scores, and a Game-Over Trap row only when one has gone
 * severe).
 */

import type {
  InspectionCompositionEntry,
  InspectionNode,
  InspectionRef,
  InspectionRow,
  InspectionSection,
} from "@/types/inspection";
import { explainRefFor } from "../provenance";
import { readConsciousness, readNumberField, readStringField, type RawEntity } from "./fields";

const CONSCIOUSNESS_COLORS = {
  revolutionary: "text-laser",
  liberal: "text-cadre",
  fascist: "text-rupture",
} as const;

const TRAP_LABELS: Record<string, string> = {
  liberal: "Liberal",
  ultra_left: "Ultra-Left",
  rightist: "Rightist",
};

interface VanguardRaw {
  cadre_labor: number;
  sympathizer_labor: number;
  reputation: number | null;
  max_cadre_labor: number;
  max_sympathizer_labor: number;
}

/** Narrow `data.vanguard` to a usable shape, or `null` (non-player org / absent). */
function readVanguard(data: RawEntity): VanguardRaw | null {
  const v = data.vanguard;
  if (v === null || v === undefined || typeof v !== "object") return null;
  const obj = v as RawEntity;
  const { cadre_labor, sympathizer_labor, max_cadre_labor, max_sympathizer_labor, reputation } =
    obj;
  if (
    typeof cadre_labor !== "number" ||
    typeof sympathizer_labor !== "number" ||
    typeof max_cadre_labor !== "number" ||
    typeof max_sympathizer_labor !== "number"
  ) {
    return null;
  }
  return {
    cadre_labor,
    sympathizer_labor,
    max_cadre_labor,
    max_sympathizer_labor,
    reputation: typeof reputation === "number" ? reputation : null,
  };
}

interface TrapStatusRaw {
  severity: string;
  score: number;
}

interface TrapsRaw {
  liberal: TrapStatusRaw;
  ultra_left: TrapStatusRaw;
  rightist: TrapStatusRaw;
  active_trap: string | null;
  game_over_trap: string | null;
}

function readTrapStatus(v: unknown): TrapStatusRaw | null {
  if (v === null || typeof v !== "object") return null;
  const { severity, score } = v as RawEntity;
  if (typeof severity !== "string" || typeof score !== "number") return null;
  return { severity, score };
}

/** Narrow `data.traps` to a usable shape, or `null` (non-player org / absent). */
function readTraps(data: RawEntity): TrapsRaw | null {
  const v = data.traps;
  if (v === null || v === undefined || typeof v !== "object") return null;
  const obj = v as RawEntity;
  const liberal = readTrapStatus(obj.liberal);
  const ultraLeft = readTrapStatus(obj.ultra_left);
  const rightist = readTrapStatus(obj.rightist);
  if (liberal === null || ultraLeft === null || rightist === null) return null;
  return {
    liberal,
    ultra_left: ultraLeft,
    rightist,
    active_trap: typeof obj.active_trap === "string" ? obj.active_trap : null,
    game_over_trap: typeof obj.game_over_trap === "string" ? obj.game_over_trap : null,
  };
}

/** [current, headroom-to-max] composition entries for a labor pool row. */
function laborComposition(current: number, max: number): InspectionCompositionEntry[] {
  return [
    { key: "Current", value: current, color: "text-spire" },
    { key: "Headroom", value: Math.max(0, max - current), color: "text-ash" },
  ];
}

function vanguardSection(vanguard: VanguardRaw): InspectionSection {
  return {
    label: "Vanguard Resources",
    rows: [
      {
        label: "Cadre Labor",
        value: null,
        format: "raw",
        composition: laborComposition(vanguard.cadre_labor, vanguard.max_cadre_labor),
      },
      {
        label: "Sympathizer Labor",
        value: null,
        format: "raw",
        composition: laborComposition(vanguard.sympathizer_labor, vanguard.max_sympathizer_labor),
      },
      { label: "Reputation", value: vanguard.reputation, format: "decimal2" },
    ],
  };
}

function trapSection(traps: TrapsRaw): InspectionSection {
  const activeTrap = traps.active_trap;
  const activeLabel =
    activeTrap === null
      ? "none"
      : `${TRAP_LABELS[activeTrap] ?? activeTrap} (${traps[activeTrap as "liberal" | "ultra_left" | "rightist"].severity})`;

  const rows: InspectionRow[] = [
    { label: "Active Trap", value: activeLabel, format: "raw" },
    { label: "Liberal", value: traps.liberal.score, format: "percent" },
    { label: "Ultra-Left", value: traps.ultra_left.score, format: "percent" },
    { label: "Rightist", value: traps.rightist.score, format: "percent" },
  ];

  if (traps.game_over_trap !== null) {
    rows.push({
      label: "Game-Over Trap",
      value: TRAP_LABELS[traps.game_over_trap] ?? traps.game_over_trap,
      format: "raw",
    });
  }

  return { label: "Trap Detection", rows };
}

export function adaptOrg(ref: InspectionRef, data: RawEntity): InspectionNode {
  const scope = `org:${ref.id}`;
  const name = readStringField(data, "name");
  const consciousness = readConsciousness(data);

  const rows: InspectionRow[] = [
    {
      label: "Class Character",
      value: readStringField(data, "class_character") ?? readStringField(data, "type"),
      format: "raw",
    },
    {
      label: "Budget",
      value: readNumberField(data, "budget") ?? readNumberField(data, "funds"),
      format: "decimal2",
    },
    { label: "Cohesion", value: readNumberField(data, "cohesion"), format: "decimal2" },
    { label: "Heat", value: readNumberField(data, "heat"), format: "decimal2" },
    {
      label: "Consciousness",
      value: null,
      format: "raw",
      composition: consciousness
        ? [
            {
              key: "Revolutionary",
              value: consciousness.revolutionary,
              color: CONSCIOUSNESS_COLORS.revolutionary,
            },
            { key: "Liberal", value: consciousness.liberal, color: CONSCIOUSNESS_COLORS.liberal },
            {
              key: "Fascist",
              value: consciousness.fascist,
              color: CONSCIOUSNESS_COLORS.fascist,
            },
          ]
        : undefined,
    },
    {
      label: "Labor Aristocracy Ratio",
      value: readNumberField(data, "labor_aristocracy_ratio"),
      format: "decimal3",
      ref: explainRefFor("labor_aristocracy_ratio", scope, "org", "Labor Aristocracy Ratio"),
    },
    {
      label: "Revolution Probability",
      value: readNumberField(data, "revolution_probability"),
      format: "decimal3",
      ref: explainRefFor("revolution_probability", scope, "org", "Revolution Probability"),
    },
    {
      label: "Acquiescence Probability",
      value: readNumberField(data, "acquiescence_probability"),
      format: "decimal3",
      ref: explainRefFor("acquiescence_probability", scope, "org", "Acquiescence Probability"),
    },
    {
      label: "Consciousness Drift",
      value: readNumberField(data, "consciousness_drift"),
      format: "decimal3",
      ref: explainRefFor("consciousness_drift", scope, "org", "Consciousness Drift"),
    },
  ];

  const sections: InspectionSection[] = [{ rows }];

  const vanguard = readVanguard(data);
  if (vanguard !== null) sections.push(vanguardSection(vanguard));

  const traps = readTraps(data);
  if (traps !== null) sections.push(trapSection(traps));

  return {
    ref,
    title: ref.label ?? name ?? ref.id,
    sections,
  };
}
