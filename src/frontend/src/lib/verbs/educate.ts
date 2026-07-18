import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";
import { parseExpectedDeltas, type WireExpectedDeltas } from "./expectedDeltas";

interface EducateTarget {
  community_id: string;
  territory_name: string;
  category: string;
  credibility: number;
  expected_deltas?: WireExpectedDeltas;
}

export const educateConfig: VerbConfig = {
  verb: "educate",
  label: "Educate",
  description:
    "Raise revolutionary consciousness in a target community through political education.",
  targetPayloadKey: "target_community_id",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as EducateTarget[];
    return targets.map((t) => ({
      id: t.community_id,
      label: `${t.territory_name} (${t.category} — Credibility: ${t.credibility})`,
      expectedDeltas: parseExpectedDeltas(t.expected_deltas),
    }));
  },
  paramFields: [],
  // EducateSubmitSerializer: org_id + target_community_id required;
  // params is an optional DictField (default {}).
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_community_id: targetId ?? "",
    params,
  }),
  // Flat {action_points, cadre_labor, sympathizer_labor, material,
  // can_afford, ...} envelope (engine_bridge.py:3216-3223).
  parseCost: parseFlatCost,
};
