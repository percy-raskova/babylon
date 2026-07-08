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
};
