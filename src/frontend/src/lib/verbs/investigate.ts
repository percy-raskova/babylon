import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";

interface InvestigateScanEntry {
  target_id: string;
  name: string;
}

interface InvestigateTargets {
  territory_scans?: InvestigateScanEntry[];
  targeted_scans?: InvestigateScanEntry[];
}

export const investigateConfig: VerbConfig = {
  verb: "investigate",
  label: "Investigate",
  description: "Gather intelligence on an enemy organization or institution.",
  targetRequired: false,
  parseTargets: (raw): VerbTarget[] => {
    // InvestigateAvailableTargetsSerializer: targets is grouped —
    // territory_scans / targeted_scans (counter_intelligence is a single
    // nullable summary object with no target id; the scan_type param
    // selects it instead).
    const groups = (raw.targets ?? {}) as InvestigateTargets;
    return [
      ...(groups.territory_scans ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Territory Scans",
      })),
      ...(groups.targeted_scans ?? []).map((t) => ({
        id: t.target_id,
        label: t.name,
        group: "Targeted Scans",
      })),
    ];
  },
  paramFields: [
    {
      key: "scan_type",
      label: "Scan Type",
      type: "select" as const,
      defaultValue: "territory_scan",
      options: [
        { value: "territory_scan", label: "Territory Scan" },
        { value: "targeted_scan", label: "Targeted Scan" },
        { value: "counter_intelligence", label: "Counter-Intelligence" },
      ],
    },
  ],
  // InvestigateSubmitSerializer: params:{scan_type} required; target_id may
  // be null (counter_intelligence scans the org itself). UI-disabled
  // (FR-025), but the builder ships now.
  buildPayload: (orgId, targetId, params) => ({
    org_id: orgId,
    target_id: targetId,
    params: { scan_type: String(params.scan_type ?? "territory_scan") },
  }),
  // Flat {action_points, cadre_labor, sympathizer_labor, material,
  // can_afford, ...} envelope (engine_bridge.py:3662-3670).
  parseCost: parseFlatCost,
  // NO predictedEffect — deliberately honest-null (owner ruling, Program
  // 17 Wave 1 item 1e). resolve_investigate (babylon/engine/actions/
  // investigate.py) performs ZERO numeric graph mutation: it is purely
  // informational (fog-of-war reveal — a `revealed` attribute-name list
  // in direct_effects, no graph.update_node call at all). There is no
  // real scalar delta to ground here, and fabricating one would violate
  // Constitution III.11 (never fabricate). See verbs.test.ts's
  // HONEST_NULL_PREDICTED_VERBS for the pinned contract.
};
