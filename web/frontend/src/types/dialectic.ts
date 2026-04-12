/**
 * V2 Dialectic Engine — TypeScript types.
 *
 * Mirrors the Pydantic models from babylon.engine.dialectics
 * for frontend consumption via the /api/v2/ endpoints.
 */

/** Observation projection from Dialectic.observe(). */
export interface DialecticObservation {
  id: string;
  type: string;
  weight: number;
  principal_aspect: "A" | "B";
  /* CommodityDialectic-specific fields */
  utility?: number;
  demand?: number;
  price?: number;
  snlt?: number;
  /* Extensible for future dialectics */
  [key: string]: unknown;
}

/** Serialized dialectic snapshot from the API. */
export interface DialecticSnapshot {
  tick: number;
  dialectic_id: string;
  type_tag: string;
  weight: number;
  observation: DialecticObservation;
  parent_id: string | null;
}

/** Morphism (edge) in the dialectical graph. */
export interface MorphismSnapshot {
  id: string;
  source_id: string;
  target_id: string;
  relation: "feeds" | "constrains" | "transforms" | "contains" | "antagonizes";
  weight: number;
}

/** Full world state response from GET /api/games/{id}/v2/world/. */
export interface DialecticWorldState {
  tick: number;
  dialectics: DialecticSnapshot[];
  morphisms: MorphismSnapshot[];
  events: Record<string, unknown>[];
}

/** Weight history point for sparkline rendering. */
export interface WeightHistoryPoint {
  tick: number;
  weight: number;
}
