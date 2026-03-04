/**
 * Lens definitions — analytical perspectives that recontextualize the UI.
 *
 * Per research.md R-004: lenses are purely frontend state. The backend returns
 * the full game state; lenses determine emphasis, layer, and ordering.
 *
 * Per research.md R-009: indicator thresholds use three tiers (normal/warning/
 * critical) with per-indicator configurable boundaries.
 */

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
      const rent = snap.economy?.imperial_rent;
      return typeof rent === "number" ? rent : 0;
    },
  },
  avg_consciousness: {
    id: "avg_consciousness",
    label: "Avg Consciousness",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      const e = snap.entities;
      return e.length > 0 ? e.reduce((s, x) => s + x.consciousness, 0) / e.length : 0;
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
      const e = snap.entities;
      return e.length > 0 ? e.reduce((s, x) => s + x.organization, 0) / e.length : 0;
    },
  },
  total_wealth: {
    id: "total_wealth",
    label: "Total Wealth",
    unit: "$",
    format: "currency",
    thresholds: { warning: 500, critical: 200, invert: true },
    compute: (snap: GameSnapshot) => snap.entities.reduce((s, e) => s + e.wealth, 0),
  },
  total_population: {
    id: "total_population",
    label: "Population",
    unit: "",
    format: "integer",
    thresholds: { warning: 0, critical: 0, invert: false },
    compute: (snap: GameSnapshot) => snap.entities.reduce((s, e) => s + e.population, 0),
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
    compute: (snap: GameSnapshot) =>
      snap.entities.reduce((max, e) => Math.max(max, e.p_revolution), 0),
  },
  p_acquiescence_min: {
    id: "p_acquiescence_min",
    label: "P(Acquiescence) Min",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.5, critical: 0.3, invert: true },
    compute: (snap: GameSnapshot) =>
      snap.entities.reduce((min, e) => Math.min(min, e.p_acquiescence), 1),
  },
  repression_avg: {
    id: "repression_avg",
    label: "Avg Repression",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.4, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      const e = snap.entities;
      return e.length > 0 ? e.reduce((s, x) => s + x.repression, 0) / e.length : 0;
    },
  },
  agitation_avg: {
    id: "agitation_avg",
    label: "Avg Agitation",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.3, critical: 0.6, invert: false },
    compute: (snap: GameSnapshot) => {
      const e = snap.entities;
      return e.length > 0 ? e.reduce((s, x) => s + x.agitation, 0) / e.length : 0;
    },
  },
  inequality_avg: {
    id: "inequality_avg",
    label: "Avg Inequality",
    unit: "",
    format: "decimal",
    thresholds: { warning: 0.4, critical: 0.7, invert: false },
    compute: (snap: GameSnapshot) => {
      const e = snap.entities;
      return e.length > 0 ? e.reduce((s, x) => s + x.inequality, 0) / e.length : 0;
    },
  },
  solidarity_edges: {
    id: "solidarity_edges",
    label: "Solidarity Edges",
    unit: "",
    format: "integer",
    thresholds: { warning: 3, critical: 1, invert: true },
    compute: (snap: GameSnapshot) => snap.edges.filter((e) => e.edge_type === "SOLIDARITY").length,
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
    inspectorPriority: ["p_revolution", "p_acquiescence", "solidarity_strength", "cohesion"],
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
