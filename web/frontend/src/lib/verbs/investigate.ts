import type { VerbConfig, VerbTarget } from "./types";

interface InvestigateTarget {
  id?: string;
  target_id?: string;
  name?: string;
}

export const investigateConfig: VerbConfig = {
  verb: "investigate",
  label: "Investigate",
  description: "Gather intelligence on an enemy organization or institution.",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as InvestigateTarget[];
    return targets.map((t) => ({
      id: t.id ?? t.target_id ?? "",
      label: t.name ?? t.id ?? t.target_id ?? "Unknown",
    }));
  },
  paramFields: [],
};
