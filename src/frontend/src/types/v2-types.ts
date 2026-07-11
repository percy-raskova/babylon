/**
 * Babylon Frontend v2 — Type Definitions
 *
 * Canonical client-side shapes from the v2 design spec.
 * Server payloads should denormalize into these types.
 */

/** Player or NPC organization. */
export interface V2Org {
  id: string;
  name: string;
  short: string;
  player_controlled: boolean;
  org_type: string;
  class_character: V2ClassCharacter;
  hq_territory: string;
  ooda_phase: "OBSERVE" | "ORIENT" | "DECIDE" | "ACT";
  cohesion: number;
  legitimacy: number;
  opacity: number;
  vanguard?: V2Vanguard;
  members: string[];
  last_action?: { tick: number; verb: string; target: string; outcome: string };
  badges: string[];
  /** NPC-only fields */
  last_observed_tick?: number;
  threat_level?: "HIGH" | "MEDIUM" | "EMERGING" | "LOW";
}

export type V2ClassCharacter =
  | "proletarian"
  | "bourgeois"
  | "comprador_bourgeois"
  | "labor_aristocracy"
  | "labor_aristocrat"
  | "lumpen";

export interface V2Vanguard {
  cl: number;
  cl_max: number;
  sl: number;
  sl_max: number;
  rep: number;
  budget: number;
  heat: number;
}

/** XGI hyperedge — community target for Educate/Mobilize/Campaign. */
export interface V2Community {
  id: string;
  name: string;
  composition: string[];
  territories: string[];
  members: number;
  con: number;
  sol: number;
  credibility_to: Record<string, number>;
  dominant_class: V2ClassCharacter;
}

/** Territory hex — dyadic graph node. */
export interface V2Territory {
  id: string;
  name: string;
  county: string;
  pop: number;
  rent: number;
  con: number;
  sol: number;
  heat: number;
  wealth: number;
  biocap: number;
  dominant_community: string;
}

/** Dyadic edge between entities. */
export interface V2Edge {
  id: string;
  type: V2EdgeType;
  source: string;
  target: string;
  intensity: number;
  rate_of_profit?: number;
  rent_burden?: number;
  value_flow_per_tick?: number;
  last_event?: string;
  age_ticks?: number;
}

export type V2EdgeType =
  "EXPLOITATION" | "SOLIDARITY" | "REPRESSION" | "TRIBUTE" | "TENANCY" | "WAGES" | "ADJACENCY";

/** Constitution Article V — nine atomic player verbs. */
export interface V2Verb {
  verb: V2VerbKey;
  label: string;
  glyph: string;
  target_type: V2TargetType;
  cost_label: string;
  desc: string;
}

export type V2VerbKey =
  | "educate"
  | "mobilize"
  | "campaign"
  | "aid"
  | "attack"
  | "move"
  | "investigate"
  | "reproduce"
  | "negotiate";

export type V2TargetType =
  "community" | "territory" | "org" | "any" | "org_or_territory" | "territory_or_community";

/** Simulation event. */
export interface V2Event {
  id: string;
  tick: number;
  type: string;
  severity: "critical" | "warning" | "good" | "info";
  title: string;
  body: string;
  actors: string[];
}

/** Queued player action — the composer's output. */
export interface V2QueuedAction {
  actorOrgId: string;
  verb: V2VerbKey;
  targetId: string;
  params: Record<string, unknown>;
}

/** Route definition for the NavRail. */
export interface V2Route {
  key: string;
  path: string;
  label: string;
  group: "pre" | "core" | "verb" | "post";
  icon: string;
}

/** Breakdown entry for Paradox-style provenance tooltips. */
export interface V2BreakdownEntry {
  label: string;
  value: number;
}

/** Resolved target item for verb target lists. */
export interface V2ResolvedTarget {
  id: string;
  type: "org" | "territory" | "community" | "edge";
  label: string;
  sub: string;
  color: string;
  meta: unknown;
  telemetry: Record<string, number>;
}

/** Verb-specific parameter schema for the compose panel. */
export interface V2VerbParam {
  key: string;
  label: string;
  kind: "radio" | "slider" | "toggle";
  options?: string[];
  min?: number;
  max?: number;
  default?: boolean | number | string;
  unit?: string;
}
