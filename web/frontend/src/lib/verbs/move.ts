import type { VerbConfig, VerbTarget } from "./types";

interface MoveTarget {
  id?: string;
  target_id?: string;
  name?: string;
  territory_name?: string;
}

export const moveConfig: VerbConfig = {
  verb: "move",
  label: "Move",
  description: "Relocate organizational presence to a new territory.",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as MoveTarget[];
    return targets.map((t) => ({
      id: t.id ?? t.target_id ?? "",
      label: t.territory_name ?? t.name ?? t.id ?? "Unknown",
    }));
  },
  paramFields: [],
};
