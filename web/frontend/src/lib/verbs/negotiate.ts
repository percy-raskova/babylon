import type { VerbConfig, VerbTarget } from "./types";

interface NegotiateTarget {
  id?: string;
  target_id?: string;
  name?: string;
}

export const negotiateConfig: VerbConfig = {
  verb: "negotiate",
  label: "Negotiate",
  description: "Engage in diplomatic negotiations with another organization.",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as NegotiateTarget[];
    return targets.map((t) => ({
      id: t.id ?? t.target_id ?? "",
      label: t.name ?? t.id ?? t.target_id ?? "Unknown",
    }));
  },
  paramFields: [],
};
