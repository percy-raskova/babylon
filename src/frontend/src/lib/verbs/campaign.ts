import type { VerbConfig, VerbTarget } from "./types";
import { makeDirectionalEffect } from "./predictedEffects";

interface GenericTarget {
  id?: string;
  target_id?: string;
  name?: string;
}

export const campaignConfig: VerbConfig = {
  verb: "campaign",
  label: "Campaign",
  description: "Launch a political campaign to build mass support and influence public discourse.",
  // Campaign has no targets GET endpoint (the route points at the submit
  // view → 405), so eligible targets come from the snapshot instead.
  targetsSource: "snapshot",
  parseTargets: (raw): VerbTarget[] => {
    const targets = (raw.targets ?? []) as GenericTarget[];
    return targets.map((t) => ({
      id: t.id ?? t.target_id ?? "",
      label: t.name ?? t.id ?? t.target_id ?? "Unknown",
    }));
  },
  paramFields: [
    {
      key: "campaign_type",
      label: "Campaign Type",
      type: "select" as const,
      defaultValue: "PUBLIC_PRESSURE",
      options: [
        { value: "ELECTORAL", label: "Electoral" },
        { value: "LEGISLATIVE", label: "Legislative" },
        { value: "PUBLIC_PRESSURE", label: "Public Pressure" },
      ],
    },
  ],
  // CampaignActionSerializer (BaseVerbActionView contract): campaign_type
  // travels FLAT — the view strips org_id/target_id and forwards the rest
  // as params_json itself. No params nesting.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    campaign_type: String(params.campaign_type ?? "PUBLIC_PRESSURE"),
  }),
  // No parseCost — campaign's GET route 405s (see the docstring comment
  // above), so `raw` never exists for this verb; useVerbTargets never
  // calls fetchVerbTargets for campaign (targetsSource: "snapshot").
  // Grounded in resolve_campaign -> resolve_action -> compute_consciousness_delta
  // (babylon/ooda/action_effects.py:80), the identical formula + tendency-sign
  // caveat as educate: assumes a revolutionary-tendency acting org
  // (tendency_modifier_revolutionary=+0.15, defines.yaml:501); a liberal org
  // (tendency_modifier_liberal=-0.05, defines.yaml:502) would see the
  // opposite sign, which Scope has no way to detect.
  predictedEffect: makeDirectionalEffect(
    "campaign.consciousness.delta",
    "Consciousness",
    "Predicted collective-identity delta on the target territory (assumes a revolutionary-tendency acting org).",
    "hex",
    1,
  ),
};
