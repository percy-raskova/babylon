import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";
import { makeDirectionalEffect } from "./predictedEffects";

interface EducateTarget {
  community_id: string;
  territory_name: string;
  category: string;
  credibility: number;
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
  // Grounded in compute_consciousness_delta (babylon/ooda/action_effects.py:80,
  // base_delta = modifier * cadre_level * cohesion * effective_credibility).
  // CAVEAT: `modifier` is tendency_modifier_revolutionary=+0.15 (defines.yaml:501)
  // for a revolutionary-tendency org, but tendency_modifier_liberal=-0.05
  // (defines.yaml:502) — a liberal-tendency acting org would see the
  // OPPOSITE sign. Scope has no acting-org id, so this arrow assumes the
  // common revolutionary-org case; it can be wrong for a liberal org.
  predictedEffect: makeDirectionalEffect(
    "educate.consciousness.delta",
    "Consciousness",
    "Predicted collective-identity delta on the target community (assumes a revolutionary-tendency acting org).",
    "hyperedge",
    1,
  ),
};
