import type { VerbConfig, VerbTarget } from "./types";

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
};
