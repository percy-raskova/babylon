/**
 * Spec 095: Dialectic screen + Endgame chronicle + Journal objectives types.
 *
 * Mirrors the contracts at:
 *   - specs/095-endgame-chronicle/contracts/contradiction.yaml
 *   - specs/095-endgame-chronicle/contracts/endgame.yaml
 *   - specs/095-endgame-chronicle/contracts/objectives.yaml
 *
 * All three are READ-ONLY endpoints — Constitution III (AI observes, never
 * controls). The Dialectic screen surfaces contradiction state the engine's
 * ContradictionSystem already computed each tick; it never computes
 * dialectical state itself.
 */

/** Dialectical regime — the phase-space classification (ADR051). */
export type DialecticalRegime = "reproduction" | "crisis" | "sublation";

/** A single opposition entry from the OppositionRegistry. */
export interface OppositionEntry {
  key: string;
  gap: number;
  rate: number;
  is_principal: boolean;
  leading_pole?: string;
}

/** One side of a contradiction frame (principal or secondary). */
export interface ContradictionAspect {
  id: string;
  aspect_a: string;
  aspect_b: string;
  principal_aspect?: string;
  intensity: number;
  aspect_balance: number;
  is_antagonistic?: boolean;
}

/** The principal + secondary contradiction frame. */
export interface ContradictionFrame {
  principal: ContradictionAspect;
  secondary: ContradictionAspect;
}

/** GET /api/games/:id/contradiction/ response body. */
export interface ContradictionSnapshot {
  tick: number;
  regime: DialecticalRegime;
  oppositions: OppositionEntry[];
  principal_key: string;
  frame: ContradictionFrame;
}

/** Terminal GameOutcome (lowercase, matching the backend enum values). */
export type TerminalOutcome =
  | "revolutionary_victory"
  | "ecological_collapse"
  | "fascist_consolidation"
  | "red_ogv"
  | "fragmented_collapse";

/** Chroncile stat cards — final-tick material summary. */
export interface EndgameStats {
  final_tick: number;
  consciousness: number;
  solidarity_edges: number;
  heat: number;
}

/** GET /api/games/:id/endgame/ response body. */
export interface EndgameState {
  tick: number;
  outcome: TerminalOutcome | null;
  headline: string;
  summary: string;
  stats: EndgameStats;
}

/** Objective status — Vic3-style tracker. */
export type ObjectiveStatus = "active" | "complete" | "failed";

/** Objective category — maps to an endgame-condition family. */
export type ObjectiveCategory = "revolution" | "collapse" | "fascist" | "red_ogv" | "fragmented";

/** A single Vic3-style objective. */
export interface Objective {
  id: string;
  title: string;
  description: string;
  progress: number;
  status: ObjectiveStatus;
  category: ObjectiveCategory;
}

/** GET /api/games/:id/objectives/ response body. */
export interface ObjectivesTracker {
  tick: number;
  objectives: Objective[];
}

/** Empty-state defaults for graceful loading. */
export const EMPTY_CONTRADICTION: ContradictionSnapshot = {
  tick: 0,
  regime: "reproduction",
  oppositions: [],
  principal_key: "",
  frame: {
    principal: {
      id: "",
      aspect_a: "",
      aspect_b: "",
      intensity: 0,
      aspect_balance: 0,
    },
    secondary: {
      id: "",
      aspect_a: "",
      aspect_b: "",
      intensity: 0,
      aspect_balance: 0,
    },
  },
};

export const EMPTY_ENDGAME: EndgameState = {
  tick: 0,
  outcome: null,
  headline: "",
  summary: "",
  stats: {
    final_tick: 0,
    consciousness: 0,
    solidarity_edges: 0,
    heat: 0,
  },
};

export const EMPTY_OBJECTIVES: ObjectivesTracker = {
  tick: 0,
  objectives: [],
};
