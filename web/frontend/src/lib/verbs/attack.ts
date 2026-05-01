import type { VerbConfig, VerbTarget } from "./types";

interface AttackTargetEntry {
  target_id: string;
  name: string;
}

interface AttackTargets {
  organizations?: AttackTargetEntry[];
  institutions?: AttackTargetEntry[];
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
};
