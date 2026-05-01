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
    const territory = scope.snapshot.territories.find((t) => t.id === scope.this!.id);
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
    const territory = scope.snapshot.territories.find((t) => t.id === scope.this!.id);
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
    const territory = scope.snapshot.territories.find((t) => t.id === scope.this!.id);
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
    const territory = scope.snapshot.territories.find((t) => t.id === scope.this!.id);
    return territory?.biocapacity ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexBiocapacity.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Biocapacity", value, `territories[${id}].biocapacity`);
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
    const org = scope.snapshot.organizations.find((o) => o.id === scope.this!.id);
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
    const org = scope.snapshot.organizations.find((o) => o.id === scope.this!.id);
    return org?.budget ?? 0;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgBudget.evaluate(scope);
    const id = scope.this?.id ?? "unknown";
    return leafBreakdown("Budget", value, `organizations[${id}].budget`);
  },
};

// ---------------------------------------------------------------------------
// Register all primitives
// ---------------------------------------------------------------------------

selectors.register(hexHeat);
selectors.register(hexRentLevel);
selectors.register(hexPopulation);
selectors.register(hexBiocapacity);
selectors.register(orgCadre);
selectors.register(orgBudget);
