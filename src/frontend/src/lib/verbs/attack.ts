import type { VerbConfig, VerbTarget } from "./types";

interface AttackTargetEntry {
  target_id: string;
  name: string;
}

interface AttackEdgeEntry {
  target_id: string;
  edge_description: string;
}

interface AttackTargets {
  organizations?: AttackTargetEntry[];
  institutions?: AttackTargetEntry[];
  edges?: AttackEdgeEntry[];
}

export const attackConfig: VerbConfig = {
  verb: "attack",
  label: "Attack",
  description: "Direct action against an enemy organization or institution.",
  parseTargets: (raw): VerbTarget[] => {
    const groups = (raw.targets ?? {}) as AttackTargets;
    return [
      ...(groups.organizations ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Organizations",
      })),
      ...(groups.institutions ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Institutions",
      })),
      ...(groups.edges ?? []).map((t) => ({
        id: t.target_id,
        label: t.edge_description,
        group: "Edges",
      })),
    ];
  },
  paramFields: [
    {
      key: "mode",
      label: "Attack Mode",
      type: "select" as const,
      defaultValue: "targeted",
      options: [
        { value: "targeted", label: "Targeted Sabotage" },
        { value: "mass", label: "Mass Action" },
      ],
    },
  ],
  // AttackSubmitSerializer: params:{mode} required; target_id may be null
  // (mass mode needs no specific target).
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId,
    params: { mode: String(params.mode ?? "targeted") },
  }),
};
