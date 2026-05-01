import type { VerbConfig, VerbTarget } from "./types";

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
};
