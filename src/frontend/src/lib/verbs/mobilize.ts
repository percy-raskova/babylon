import type { LiveVerbCost, VerbConfig, VerbTarget } from "./types";

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
};
