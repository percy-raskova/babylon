import type { VerbConfig, VerbTarget } from "./types";

interface MobilizeTarget {
  id: string;
  name: string;
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
};
