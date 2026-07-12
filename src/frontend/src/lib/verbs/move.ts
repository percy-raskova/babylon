import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";
import { makeDirectionalEffect } from "./predictedEffects";

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
  // Grounded in resolve_move (babylon/engine/actions/move.py:64-66):
  // "expand" mode appends to territory_ids — territorial presence grows
  // by at most 1. scopeKind "global" — no real per-org presence count is
  // reachable from Scope. FLAG: true only for the DEFAULT "expand" mode;
  // "relocate" mode REPLACES territory_ids (count stays flat, does not
  // grow) and evaluate() cannot see the mode param — the weakest-grounded
  // non-null verb after investigate/negotiate.
  predictedEffect: makeDirectionalEffect(
    "move.territorial_presence.delta",
    "Territorial Presence",
    "Predicted growth in the acting org's territory count (assumes the default 'expand' mode).",
    "global",
    1,
  ),
};
