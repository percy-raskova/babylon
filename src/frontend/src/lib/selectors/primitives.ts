/**
 * Primitive selectors — read a single field from the snapshot.
 *
 * Each primitive registers itself in the global selector registry.
 * All produce a flat breakdown with a single contributor.
 */

import { selectors } from "./registry";
import type { ScriptValue, Scope, Breakdown, Contributor } from "./types";

// ---------------------------------------------------------------------------
// Helper — build a single-contributor breakdown (leaf node)
// ---------------------------------------------------------------------------

function leafBreakdown(label: string, value: number, path: string): Breakdown {
  const contributor: Contributor = {
    label,
    value,
    share: 1.0,
    source: { kind: "snapshot_field", path },
    children: [],
  };
  return { total: value, contributors: [contributor] };
}

// ---------------------------------------------------------------------------
// Hex primitives
// ---------------------------------------------------------------------------

const hexHeat: ScriptValue = {
  name: "hex.heat",
  label: "Heat",
  description: "Territory heat level (0-1 normalized).",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId);
    return territory?.heat ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexHeat.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Heat", value, `territories[${id}].heat`);
  },
};

const hexRentLevel: ScriptValue = {
  name: "hex.rent_level",
  label: "Rent Level",
  description: "Territory rent extraction level (0-1 normalized).",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId);
    return territory?.rent_level ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexRentLevel.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Rent Level", value, `territories[${id}].rent_level`);
  },
};

const hexPopulation: ScriptValue = {
  name: "hex.population",
  label: "Population",
  description: "Territory population count.",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId);
    return territory?.population ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexPopulation.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Population", value, `territories[${id}].population`);
  },
};

const hexBiocapacity: ScriptValue = {
  name: "hex.biocapacity",
  label: "Biocapacity",
  description: "Territory ecological carrying capacity (0-1 normalized).",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId);
    return territory?.biocapacity ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexBiocapacity.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Biocapacity", value, `territories[${id}].biocapacity`);
  },
};

/** Loosely-typed territory shape for fields the backend snapshot may carry
 * beyond the strict `TerritoryState` interface (matches the existing
 * `SnapshotTerritory` convention in `IntelPageV2.tsx`). */
interface LooseTerritory {
  wealth?: number;
  consciousness?: number;
}

const hexWealth: ScriptValue = {
  name: "hex.wealth",
  label: "Wealth",
  description: "Territory-scoped accumulated wealth.",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId) as
      | (LooseTerritory & { id: string })
      | undefined;
    return territory?.wealth ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexWealth.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Wealth", value, `territories[${id}].wealth`);
  },
};

const hexConsciousness: ScriptValue = {
  name: "hex.consciousness",
  label: "Consciousness",
  description: "Territory-scoped consciousness level (0-1 normalized).",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const scopeId = scope.this.id;
    const territory = scope.snapshot.territories.find((t) => t.id === scopeId) as
      | (LooseTerritory & { id: string })
      | undefined;
    return territory?.consciousness ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexConsciousness.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Consciousness", value, `territories[${id}].consciousness`);
  },
};

// ---------------------------------------------------------------------------
// Org primitives
// ---------------------------------------------------------------------------

const orgCadre: ScriptValue = {
  name: "org.cadre",
  label: "Cadre Level",
  description: "Organization cadre development level.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const scopeId = scope.this.id;
    const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
    return org?.cadre_level ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgCadre.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Cadre Level", value, `organizations[${id}].cadre_level`);
  },
};

const orgBudget: ScriptValue = {
  name: "org.budget",
  label: "Budget",
  description: "Organization budget in material units.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const scopeId = scope.this.id;
    const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
    return org?.budget ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgBudget.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Budget", value, `organizations[${id}].budget`);
  },
};

const orgHeat: ScriptValue = {
  name: "org.heat",
  label: "Heat",
  description: "Organization state-attention level (0-1 normalized).",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const scopeId = scope.this.id;
    const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
    return org?.heat ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgHeat.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Heat", value, `organizations[${id}].heat`);
  },
};

const orgCohesion: ScriptValue = {
  name: "org.cohesion",
  label: "Cohesion",
  description: "Organization internal cohesion (0-1 normalized).",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const scopeId = scope.this.id;
    const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
    return org?.cohesion ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgCohesion.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Cohesion", value, `organizations[${id}].cohesion`);
  },
};

const orgOpacity: ScriptValue = {
  name: "org.opacity",
  label: "Opacity",
  description: "Organization counter-intelligence opacity (0-1 normalized).",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const scopeId = scope.this.id;
    const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
    return org?.opacity ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgOpacity.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Opacity", value, `organizations[${id}].opacity`);
  },
};

function vanguardField(
  scope: Scope,
  field: "cadre_labor" | "sympathizer_labor" | "reputation",
): number {
  if (!scope.this || scope.this.kind !== "org") return 0;
  const scopeId = scope.this.id;
  const org = scope.snapshot.organizations.find((o) => o.id === scopeId);
  return org?.vanguard?.[field] ?? 0;
}

const orgVanguardCadreLabor: ScriptValue = {
  name: "org.vanguard_cadre_labor",
  label: "Cadre Labor",
  description: "Vanguard-economy cadre labor pool.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => vanguardField(scope, "cadre_labor"),
  breakdown: (scope: Scope): Breakdown => {
    const value = vanguardField(scope, "cadre_labor");
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Cadre Labor", value, `organizations[${id}].vanguard.cadre_labor`);
  },
};

const orgVanguardSympathizerLabor: ScriptValue = {
  name: "org.vanguard_sympathizer_labor",
  label: "Sympathizer Labor",
  description: "Vanguard-economy sympathizer labor pool.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => vanguardField(scope, "sympathizer_labor"),
  breakdown: (scope: Scope): Breakdown => {
    const value = vanguardField(scope, "sympathizer_labor");
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown(
      "Sympathizer Labor",
      value,
      `organizations[${id}].vanguard.sympathizer_labor`,
    );
  },
};

const orgVanguardReputation: ScriptValue = {
  name: "org.vanguard_reputation",
  label: "Reputation",
  description: "Vanguard-economy reputation (0-1 normalized).",
  scopeKind: "org",
  evaluate: (scope: Scope): number => vanguardField(scope, "reputation"),
  breakdown: (scope: Scope): Breakdown => {
    const value = vanguardField(scope, "reputation");
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Reputation", value, `organizations[${id}].vanguard.reputation`);
  },
};

// ---------------------------------------------------------------------------
// Register all primitives
// ---------------------------------------------------------------------------

selectors.register(hexHeat);
selectors.register(hexRentLevel);
selectors.register(hexPopulation);
selectors.register(hexBiocapacity);
selectors.register(hexWealth);
selectors.register(hexConsciousness);
selectors.register(orgCadre);
selectors.register(orgBudget);
selectors.register(orgHeat);
selectors.register(orgCohesion);
selectors.register(orgOpacity);
selectors.register(orgVanguardCadreLabor);
selectors.register(orgVanguardSympathizerLabor);
selectors.register(orgVanguardReputation);
