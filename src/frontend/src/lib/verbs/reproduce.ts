import type { VerbConfig, VerbTarget } from "./types";
import { parseFlatCost } from "./cost";
import { makeDirectionalEffect } from "./predictedEffects";

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
  // Top-level cost is `sympathizer_labor:10.0` (flat envelope,
  // engine_bridge.py:3587-3595) — NOT the same as the per-mode
  // `resource_cost` nested under targets[0].modes, which parseFlatCost
  // does not read.
  parseCost: parseFlatCost,
  // Grounded in resolve_reproduce's cadre_training branch (babylon/engine/
  // actions/reproduce.py:88-91, the paramFields default mode): unconditionally
  // raises both cadre_level and cohesion. targetRequired is already false.
  // FLAG PROMINENTLY: if the player switches the mode dropdown to
  // mass_recruitment, the REAL engine effect FLIPS (reproduce.py:67-86 —
  // cohesion DECREASES, no cadre change), but evaluate() never sees
  // paramVals and will keep showing ▲ Cadre. This is the one verb where
  // the arrow can become actively WRONG (not just imprecise) once the
  // player changes the mode — a known limitation of the frozen
  // evaluatePredictedEffect(config, snapshot, targetId) signature.
  predictedEffect: makeDirectionalEffect(
    "reproduce.cadre.delta",
    "Cadre",
    "Predicted cadre_level/cohesion increase (assumes the default 'cadre_training' mode).",
    "global",
    1,
  ),
};
