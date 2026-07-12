import type { LiveVerbCost, VerbConfig, VerbTarget } from "./types";
import { makeDirectionalEffect } from "./predictedEffects";

interface MobilizeTarget {
  id: string;
  name: string;
}

/** mobilize's cost rides TOP-LEVEL fields (mobilize_cost_cl, available_cl),
 *  NOT under a `cost` key like every other verb (engine_bridge.py:3443-3449;
 *  GameDefines().mobilize.mobilize_cl_cost = 0.2 per defines.yaml:56). */
function parseMobilizeCost(raw: Record<string, unknown>): LiveVerbCost | null {
  const mobilizeCostCl = raw.mobilize_cost_cl;
  const availableCl = raw.available_cl;
  if (typeof mobilizeCostCl !== "number") return null;

  return {
    label: `${mobilizeCostCl} CL`,
    canAfford: typeof availableCl === "number" && availableCl >= mobilizeCostCl,
  };
}

export const mobilizeConfig: VerbConfig = {
  verb: "mobilize",
  label: "Mobilize",
  description: "Deploy sympathizer labor for direct action or organizational tasks.",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as MobilizeTarget[];
    return targets.map((t) => ({
      id: t.id,
      label: t.name,
    }));
  },
  paramFields: [
    {
      key: "sl_committed",
      label: "Sympathizer Labor Committed",
      type: "number" as const,
      defaultValue: 0,
      min: 0,
    },
  ],
  // MobilizeSubmitSerializer: params:{sl_committed: float} is REQUIRED.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    params: { sl_committed: Number(params.sl_committed ?? 0) },
  }),
  parseCost: parseMobilizeCost,
  // Grounded in resolve_mobilize (babylon/engine/actions/mobilize.py:78):
  // new_heat = min(1.0, heat + heat_generated) — backfire only multiplies
  // heat_generated, never flips its sign. mobilize's targets ARE real
  // business/civil_society org ids — the cleanest scope-match of the 9.
  // CAVEAT: sl_committed defaults to 0 (this verb's paramFields default),
  // so at the DEFAULT param state the real delta is exactly 0 — this
  // constant arrow shows slightly eagerly, before the player raises the
  // slider (evaluate() cannot see paramVals — see predictedEffects.ts).
  predictedEffect: makeDirectionalEffect(
    "mobilize.heat.delta",
    "Heat",
    "Predicted state-attention (heat) increase on the target from mobilized turnout.",
    "org",
    1,
  ),
};
