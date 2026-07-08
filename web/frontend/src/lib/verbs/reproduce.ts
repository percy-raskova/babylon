import type { VerbConfig, VerbTarget } from "./types";

interface ReproduceTarget {
  target_id: string;
  name: string;
}

export const reproduceConfig: VerbConfig = {
  verb: "reproduce",
  label: "Reproduce",
  description: "Maintain and reproduce organizational capacity through internal development.",
  targetRequired: false,
  parseTargets: (raw): VerbTarget[] => {
    // ReproduceTargetSerializer: the self-target list (the acting org).
    const targets = (raw.targets ?? []) as ReproduceTarget[];
    return targets.map((t) => ({
      id: t.target_id,
      label: t.name,
    }));
  },
  paramFields: [
    {
      key: "mode",
      label: "Mode",
      type: "select" as const,
      defaultValue: "cadre_training",
      options: [
        { value: "cadre_training", label: "Cadre Training" },
        { value: "mass_recruitment", label: "Mass Recruitment" },
      ],
    },
    {
      key: "cl_committed",
      label: "Cadre Labor Committed",
      type: "number" as const,
      defaultValue: 0,
      min: 0,
    },
    {
      key: "sl_committed",
      label: "Sympathizer Labor Committed",
      type: "number" as const,
      defaultValue: 0,
      min: 0,
    },
  ],
  // ReproduceSubmitSerializer: params:{mode, cl_committed?, sl_committed?}
  // required; target_id optional — omitted entirely when self-targeting.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    ...(targetId ? { target_id: targetId } : {}),
    params: {
      mode: String(params.mode ?? "cadre_training"),
      cl_committed: Number(params.cl_committed ?? 0),
      sl_committed: Number(params.sl_committed ?? 0),
    },
  }),
};
