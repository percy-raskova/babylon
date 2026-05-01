import type { VerbConfig, VerbTarget } from "./types";

interface GenericTarget {
  id?: string;
  target_id?: string;
  name?: string;
}

export const campaignConfig: VerbConfig = {
  verb: "campaign",
  label: "Campaign",
  description: "Launch a political campaign to build mass support and influence public discourse.",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as GenericTarget[];
    return targets.map((t) => ({
      id: t.id ?? t.target_id ?? "",
      label: t.name ?? t.id ?? t.target_id ?? "Unknown",
    }));
  },
  paramFields: [],
};
