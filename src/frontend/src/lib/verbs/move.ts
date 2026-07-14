import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";

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
  paramFields: [
    {
      key: "mode",
      label: "Move Mode",
      type: "select" as const,
      defaultValue: "expand",
      options: [
        { value: "expand", label: "Expand" },
        { value: "relocate", label: "Relocate" },
      ],
    },
  ],
  // MoveSubmitSerializer: params:{mode} required. UI-disabled (FR-025),
  // but the builder ships now so enabling later is a one-line set change.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    params: { mode: String(params.mode ?? "expand") },
  }),
  // Flat {action_points, cadre_labor, sympathizer_labor, material,
  // can_afford, ...} envelope (engine_bridge.py:3751-3759).
  parseCost: parseFlatCost,
};
