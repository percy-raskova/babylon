/**
 * Lens definitions — analytical perspectives that recontextualize the UI.
 *
 * Per research.md R-004: lenses are purely frontend state. The backend returns
 * the full game state; lenses determine emphasis, layer, and ordering.
 *
 * Per research.md R-009: indicator thresholds use three tiers (normal/warning/
 * critical) with per-indicator configurable boundaries.
 *
 * Updated for **Spec 052 — WorldState Snapshot Contract v0**:
 * - Indicators that previously read from `snap.entities` now read from
 *   `snap.derived.class_aggregates` or `snap.organizations`.
 * - Economy data reads from `snap.derived.economy` / `snap.derived.imperial_rent`.
 * - Edge types use the new `mode` enum.
 */

import { rampForLayer } from "@/theme/colors";
import type {
  GameSnapshot,
  LensDefinition,
  LensId,
  IndicatorDefinition,
  IndicatorId,
} from "@/types/game";

// ---------------------------------------------------------------------------
// Indicator definitions (compute functions + thresholds)
// ---------------------------------------------------------------------------

export const INDICATOR_DEFINITIONS: Record<IndicatorId, IndicatorDefinition> = {
  imperial_rent: {
    id: "imperial_rent",
    label: "Imperial Rent",
    unit: "$",
    format: "currency",
    thresholds: { warning: 0.5, critical: 0.8, invert: false },
    compute: (snap: GameSnapshot) => {
      return snap.derived?.imperial_rent?.total ?? 0;
    },
  },
  avg_consciousness: {
    id: "avg_consciousness",
    label: "Avg Consciousness",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      // Average revolutionary consciousness across all organizations
      const orgs = snap.organizations;
      if (orgs.length === 0) return 0;
      return orgs.reduce((s, o) => s + (o.consciousness?.revolutionary ?? 0), 0) / orgs.length;
    },
  },
  avg_heat: {
    id: "avg_heat",
    label: "Avg Heat",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.6, invert: false },
    compute: (snap: GameSnapshot) => {
      const t = snap.territories;
      return t.length > 0 ? t.reduce((s, x) => s + x.heat, 0) / t.length : 0;
    },
  },
  avg_organization: {
    id: "avg_organization",
    label: "Avg Organization",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.5, critical: 0.3, invert: true },
    compute: (snap: GameSnapshot) => {
      // Use cadre_level as proxy for organizational capacity
      const orgs = snap.organizations;
      if (orgs.length === 0) return 0;
      return orgs.reduce((s, o) => s + o.cadre_level, 0) / orgs.length;
    },
  },
  total_wealth: {
    id: "total_wealth",
    label: "Total Wealth",
    unit: "$",
    format: "currency",
    thresholds: { warning: 500, critical: 200, invert: true },
    compute: (snap: GameSnapshot) => snap.organizations.reduce((s, o) => s + o.budget, 0),
  },
  total_population: {
    id: "total_population",
    label: "Population",
    unit: "",
    format: "integer",
    thresholds: { warning: 0, critical: 0, invert: false },
    compute: (snap: GameSnapshot) => {
      // Sum from derived class aggregates
      const aggs = snap.derived?.class_aggregates ?? {};
      return Object.values(aggs).reduce((s, c) => s + (c.population ?? 0), 0);
    },
  },
  org_count: {
    id: "org_count",
    label: "Organizations",
    unit: "",
    format: "integer",
    thresholds: { warning: 3, critical: 1, invert: true },
    compute: (snap: GameSnapshot) => snap.organizations.length,
  },
  edge_count: {
    id: "edge_count",
    label: "Relationships",
    unit: "",
    format: "integer",
    thresholds: { warning: 0, critical: 0, invert: false },
    compute: (snap: GameSnapshot) => snap.edges.length,
  },
  eviction_rate: {
    id: "eviction_rate",
    label: "Eviction Rate",
    unit: "%",
    format: "percent",
    thresholds: { warning: 0.1, critical: 0.3, invert: false },
    compute: (snap: GameSnapshot) => {
      const t = snap.territories;
      return t.length > 0 ? t.filter((x) => x.under_eviction).length / t.length : 0;
    },
  },
  biocapacity_avg: {
    id: "biocapacity_avg",
    label: "Biocapacity",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.4, critical: 0.2, invert: true },
    compute: (snap: GameSnapshot) => {
      const t = snap.territories;
      return t.length > 0 ? t.reduce((s, x) => s + x.biocapacity, 0) / t.length : 0;
    },
  },
  p_revolution_max: {
    id: "p_revolution_max",
    label: "P(Revolution) Max",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.6, invert: false },
    compute: (snap: GameSnapshot) => {
      // Max p_revolution from per-hyperedge predictions
      const preds = snap.derived?.predictions?.per_hyperedge ?? {};
      return Object.values(preds).reduce((max, p) => Math.max(max, p.p_revolution ?? 0), 0);
    },
  },
  p_acquiescence_min: {
    id: "p_acquiescence_min",
    label: "P(Acquiescence) Min",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.5, critical: 0.3, invert: true },
    compute: (snap: GameSnapshot) => {
      // Min p_acquiescence from per-hyperedge predictions
      const preds = snap.derived?.predictions?.per_hyperedge ?? {};
      const vals = Object.values(preds);
      if (vals.length === 0) return 1;
      return vals.reduce((min, p) => Math.min(min, p.p_acquiescence ?? 1), 1);
    },
  },
  repression_avg: {
    id: "repression_avg",
    label: "Avg Repression",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.4, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      // Average repression_flow across edges
      const edges = snap.edges;
      if (edges.length === 0) return 0;
      return edges.reduce((s, e) => s + (e.repression_flow ?? 0), 0) / edges.length;
    },
  },
  agitation_avg: {
    id: "agitation_avg",
    label: "Avg Agitation",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.6, invert: false },
    compute: (snap: GameSnapshot) => {
      // Average agitation_proxy from derived class aggregates
      const aggs = snap.derived?.class_aggregates ?? {};
      const vals = Object.values(aggs);
      if (vals.length === 0) return 0;
      return vals.reduce((s, c) => s + (c.agitation_proxy ?? 0), 0) / vals.length;
    },
  },
  inequality_avg: {
    id: "inequality_avg",
    label: "Avg Inequality",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.4, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      return snap.derived?.economy?.gini ?? 0;
    },
  },
  solidarity_edges: {
    id: "solidarity_edges",
    label: "Solidarity Edges",
    unit: "",
    format: "integer",
    thresholds: { warning: 3, critical: 1, invert: true },
    compute: (snap: GameSnapshot) => snap.edges.filter((e) => e.mode === "SOLIDARISTIC").length,
  },
};

// ---------------------------------------------------------------------------
// Lens definitions
// ---------------------------------------------------------------------------

export const LENS_DEFINITIONS: Record<LensId, LensDefinition> = {
  economic: {
    id: "economic",
    name: "Economic",
    icon: "DollarSign",
    primaryLayer: "rent",
    emphasizedIndicators: ["imperial_rent", "total_wealth", "inequality_avg", "eviction_rate"],
    inspectorPriority: ["wealth", "rent_level", "value_flow", "budget"],
    defaultChartMetrics: ["imperial_rent", "total_wealth", "inequality_avg"],
    description: "View extraction, wealth distribution, and economic flows",
  },
  political: {
    id: "political",
    name: "Political",
    icon: "Vote",
    primaryLayer: "consciousness",
    emphasizedIndicators: [
      "avg_consciousness",
      "avg_organization",
      "agitation_avg",
      "repression_avg",
    ],
    inspectorPriority: ["consciousness", "organization", "agitation", "repression"],
    defaultChartMetrics: ["avg_consciousness", "avg_organization", "agitation_avg"],
    description: "View consciousness, organization, and political dynamics",
  },
  social: {
    id: "social",
    name: "Social",
    icon: "Users",
    primaryLayer: "heat",
    emphasizedIndicators: ["avg_heat", "eviction_rate", "biocapacity_avg", "total_population"],
    inspectorPriority: ["heat", "under_eviction", "biocapacity", "population"],
    defaultChartMetrics: ["avg_heat", "eviction_rate", "biocapacity_avg"],
    description: "View heat, eviction pressure, and social conditions",
  },
  strategic: {
    id: "strategic",
    name: "Strategic",
    icon: "Target",
    primaryLayer: "consciousness",
    emphasizedIndicators: [
      "p_revolution_max",
      "p_acquiescence_min",
      "solidarity_edges",
      "org_count",
    ],
    inspectorPriority: ["p_revolution", "p_acquiescence", "cohesion", "tension"],
    defaultChartMetrics: ["p_revolution_max", "p_acquiescence_min", "solidarity_edges"],
    description: "View revolutionary potential, solidarity, and strategic balance",
  },
};

/** Ordered list of all lenses for UI rendering. */
export const LENS_LIST: LensDefinition[] = [
  LENS_DEFINITIONS.economic,
  LENS_DEFINITIONS.political,
  LENS_DEFINITIONS.social,
  LENS_DEFINITIONS.strategic,
];

/** Ordered list of all indicator definitions. */
export const INDICATOR_LIST: IndicatorDefinition[] = Object.values(INDICATOR_DEFINITIONS);

/** Get a lens definition by ID. */
export function getLensById(id: LensId): LensDefinition {
  return LENS_DEFINITIONS[id];
}

// ---------------------------------------------------------------------------
// Cold Collapse data ramps (spec-090)
//
// Each lens's map legend renders the SAME canonical luminance-monotonic ramp
// that the deck.gl fill uses, resolved from the lens's `primaryLayer` — a
// single source of truth shared with `theme/colors.ts` (`rampForLayer`).
// ---------------------------------------------------------------------------

/** The canon ramp (hex stops) for each lens, keyed by lens id. */
export const LENS_RAMP_STOPS: Record<LensId, string[]> = {
  economic: rampForLayer(LENS_DEFINITIONS.economic.primaryLayer),
  political: rampForLayer(LENS_DEFINITIONS.political.primaryLayer),
  social: rampForLayer(LENS_DEFINITIONS.social.primaryLayer),
  strategic: rampForLayer(LENS_DEFINITIONS.strategic.primaryLayer),
};

/** Get the canon data ramp (hex stops) for a lens's primary map layer. */
export function getLensRampStops(id: LensId): string[] {
  return rampForLayer(LENS_DEFINITIONS[id].primaryLayer);
}

/** Get an indicator definition by ID. */
export function getIndicatorById(id: IndicatorId): IndicatorDefinition {
  return INDICATOR_DEFINITIONS[id];
}

/**
 * Determine urgency level for an indicator value.
 * Returns "normal", "warning", or "critical".
 */
export function getIndicatorUrgency(
  value: number,
  thresholds: IndicatorDefinition["thresholds"],
): "normal" | "warning" | "critical" {
  if (thresholds.invert) {
    if (value <= thresholds.critical) return "critical";
    if (value <= thresholds.warning) return "warning";
    return "normal";
  }
  if (value >= thresholds.critical) return "critical";
  if (value >= thresholds.warning) return "warning";
  return "normal";
}

/**
 * Format an indicator value for display.
 */
export function formatIndicatorValue(value: number, format: IndicatorDefinition["format"]): string {
  switch (format) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "integer":
      return Math.round(value).toLocaleString();
    case "currency":
      return `$${value.toFixed(1)}`;
    case "decimal":
      return value.toFixed(2);
  }
}
