import type { LiveVerbCost, VerbConfig, VerbTarget } from "./types";
import { makeDirectionalEffect } from "./predictedEffects";

interface AttackTargetEntry {
  target_id: string;
  name: string;
}

interface AttackEdgeEntry {
  target_id: string;
  edge_description: string;
}

interface AttackTargets {
  organizations?: AttackTargetEntry[];
  institutions?: AttackTargetEntry[];
  edges?: AttackEdgeEntry[];
}

/** attack's cost shape is NOT the shared flat envelope — it carries both
 *  a targeted-mode cost (cadre labor) and a mass-mode cost (sympathizer
 *  labor) plus a shared material cost (engine_bridge.py:3464-3473,
 *  under the same top-level `cost` key as the other verbs). */
interface AttackCost {
  cadre_labor_if_targeted?: number;
  sympathizer_labor_if_mass?: number;
  material?: number;
  can_afford_targeted?: boolean;
  can_afford_mass?: boolean;
}

function parseAttackCost(raw: Record<string, unknown>): LiveVerbCost | null {
  const cost = raw.cost;
  if (!cost || typeof cost !== "object") return null;

  const c = cost as AttackCost;
  const parts: string[] = [];
  if (c.cadre_labor_if_targeted) parts.push(`${c.cadre_labor_if_targeted} CL`);
  if (c.sympathizer_labor_if_mass) parts.push(`${c.sympathizer_labor_if_mass} SL`);
  const label = parts.length > 0 ? parts.join(" / ") : "Free";

  return { label, canAfford: Boolean(c.can_afford_targeted || c.can_afford_mass) };
}

export const attackConfig: VerbConfig = {
  verb: "attack",
  label: "Attack",
  description: "Direct action against an enemy organization or institution.",
  parseTargets: (raw): VerbTarget[] => {
    const groups = (raw.targets ?? {}) as AttackTargets;
    return [
      ...(groups.organizations ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Organizations",
      })),
      ...(groups.institutions ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Institutions",
      })),
      ...(groups.edges ?? []).map((t) => ({
        id: t.target_id,
        label: t.edge_description,
        group: "Edges",
      })),
    ];
  },
  paramFields: [
    {
      key: "mode",
      label: "Attack Mode",
      type: "select" as const,
      defaultValue: "targeted",
      options: [
        { value: "targeted", label: "Targeted Sabotage" },
        { value: "mass", label: "Mass Action" },
      ],
    },
  ],
  // AttackSubmitSerializer: params:{mode} required; target_id may be null
  // (mass mode needs no specific target).
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId,
    params: { mode: String(params.mode ?? "targeted") },
  }),
  parseCost: parseAttackCost,
  // Grounded in resolve_attack (babylon/engine/actions/attack.py:56-59):
  // new_heat = min(1.0, heat + _ATTACK_SELF_HEAT_GAIN) — unconditional,
  // the single most solidly-grounded verb of the 9. NOTE: this metric
  // describes the ACTING org's heat, not the target's — a scope mismatch
  // inherent to attack having no target-side scalar effect (layer 3's
  // infrastructure decrement is not modeled here).
  predictedEffect: makeDirectionalEffect(
    "attack.self_heat.delta",
    "Heat",
    "Predicted state-attention (heat) increase on the ACTING org from launching an attack.",
    "org",
    1,
  ),
};
