/**
 * Curated difficulty presets (spec-116 FR-116-3).
 *
 * The lobby exposes difficulty ONLY through this vetted map — never a raw
 * defines editor. Each `defines` object is a partial GameDefines override,
 * validated server-side by `GameDefines(**defines)` inside
 * `EngineBridge.create_game` (engine_bridge.py:1975) — which is AFTER
 * serializer validation, so an invalid value would surface as a 500 (recon
 * gotcha). Every value here therefore stays inside the schema's declared
 * field constraints, so a preset can never 500 the create call:
 *
 *  - `consciousness.sensitivity`      ge=0, le=1, default 0.5
 *  - `economy.extraction_efficiency`  ge=0, le=1, default 0.8
 *  - `survival.default_subsistence`   ge=0, le=1, default 0.3
 *
 * (src/babylon/config/defines/{consciousness,economy_basic,survival}.py —
 * the same three knobs tools/regression_test.py's scenario overrides already
 * exercise, so their validity is regression-proven.)
 */

export interface DifficultyPreset {
  key: string;
  label: string;
  description: string;
  defines: Record<string, unknown>;
}

export const DIFFICULTY_PRESETS: readonly DifficultyPreset[] = [
  {
    key: "agitator",
    label: "AGITATOR",
    description: "Consciousness drifts faster — a forgiving conjuncture",
    defines: { consciousness: { sensitivity: 0.7 } },
  },
  {
    key: "cadre",
    label: "CADRE",
    description: "The standard conjuncture — schema defaults untouched",
    defines: {},
  },
  {
    key: "besieged",
    label: "BESIEGED",
    description: "Deeper extraction, thinner margins of survival",
    defines: {
      economy: { extraction_efficiency: 0.9 },
      survival: { default_subsistence: 0.4 },
    },
  },
];

/**
 * Fresh 31-bit rng seed for a new session (spec-061 FR-024 threading). The
 * historical default of 0-for-everyone made per-session replay seeds
 * meaningless; the lobby now rolls one at create time. (Codenames derive from
 * the session UUID server-side — the seed drives engine replay determinism,
 * not naming.)
 */
export function rollRngSeed(): number {
  // eslint-disable-next-line sonarjs/pseudo-random -- not security-sensitive: seeds the engine's own deterministic RNG for replay, never auth/crypto material.
  return Math.floor(Math.random() * 2147483647);
}
