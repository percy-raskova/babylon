import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";

interface AidPopTarget {
  community_id: string;
  community_name: string;
}

interface AidOrgTarget {
  org_id: string;
  org_name: string;
}

export const aidConfig: VerbConfig = {
  verb: "aid",
  label: "Aid",
  description: "Transfer material resources to a community or allied organization.",
  parseTargets: (raw): VerbTarget[] => {
    const popTargets = (raw.population_targets ?? []) as AidPopTarget[];
    const orgTargets = (raw.org_targets ?? []) as AidOrgTarget[];
    return [
      ...popTargets.map((t) => ({
        id: t.community_id,
        label: t.community_name,
        group: "Communities",
      })),
      ...orgTargets.map((t) => ({
        id: t.org_id,
        label: t.org_name,
        group: "Organizations",
      })),
    ];
  },
  paramFields: [
    {
      key: "transfer_amount",
      label: "Transfer Amount",
      type: "number" as const,
      defaultValue: 0,
      min: 0,
    },
  ],
  // AidSubmitSerializer: params:{transfer_amount: float} is REQUIRED —
  // the amount rides nested under params, never flat.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    params: { transfer_amount: Number(params.transfer_amount ?? 0) },
  }),
  // Flat {action_points, cadre_labor, sympathizer_labor, material,
  // can_afford, ...} envelope (engine_bridge.py:3315-3323).
  parseCost: parseFlatCost,
};
