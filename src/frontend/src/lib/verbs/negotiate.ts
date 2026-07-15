import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";

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
  paramFields: [
    {
      key: "proposal",
      label: "Proposal",
      type: "select" as const,
      defaultValue: "coordination_pact",
      options: [
        { value: "coordination_pact", label: "Coordination Pact" },
        { value: "resource_sharing", label: "Resource Sharing" },
        { value: "ceasefire", label: "Ceasefire" },
        { value: "demand_policy_change", label: "Demand Policy Change" },
        { value: "reconciliation", label: "Reconciliation" },
      ],
    },
  ],
  // NegotiateSubmitSerializer: params:{proposal} required. UI-disabled
  // (FR-025), but the builder ships now.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    params: { proposal: String(params.proposal ?? "coordination_pact") },
  }),
  // Flat {action_points, cadre_labor, sympathizer_labor, material,
  // can_afford, ...} envelope (engine_bridge.py:3805-3813 — cost is
  // always free/can_afford:true for negotiate).
  parseCost: parseFlatCost,
  // resolve_negotiate (babylon/engine/actions/negotiate.py) only flips
  // `edge_type` on success (leverage-gated) — no continuous metric is
  // written at all (EdgeState.tension exists in the type but the resolver
  // never touches it). The live `/actions/preview/` chip (Program 17 Wave
  // 1 item W1.2) is expected to show no delta for this verb, same as
  // investigate — an honest reflection of the real engine effect.
};
