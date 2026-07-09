/**
 * Derived selectors — compose primitives and snapshot data into
 * multi-contributor breakdowns.
 *
 * Each derived selector registers itself in the global registry.
 */

import { selectors } from "./registry";
import { GAMEDEFINES } from "./gamedefines";
import type { ScriptValue, Scope, Breakdown, Contributor } from "./types";

// ---------------------------------------------------------------------------
// hex.imperial_rent — per-territory share of total imperial rent
// ---------------------------------------------------------------------------

function buildRentContributor(
  label: string,
  component: number,
  total: number,
  share: number,
  path: string,
): Contributor {
  return {
    label,
    value: component * share,
    share: total > 0 ? component / total : 0,
    source: { kind: "snapshot_field", path },
    children: [],
  };
}

const hexImperialRent: ScriptValue = {
  name: "hex.imperial_rent",
  label: "Imperial Rent (Territory Share)",
  description:
    "This territory's proportional share of total imperial rent, distributed by rent_level ratio.",
  scopeKind: "hex",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "hex") return 0;
    const snap = scope.snapshot;
    const territory = snap.territories.find((t) => t.id === scope.this!.id);
    if (!territory) return 0;

    const totalRent = snap.derived?.imperial_rent?.total ?? 0;
    if (totalRent === 0) return 0;

    const totalRentLevel = snap.territories.reduce((s, t) => s + t.rent_level, 0);
    if (totalRentLevel === 0) return 0;

    return (territory.rent_level / totalRentLevel) * totalRent;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = hexImperialRent.evaluate(scope);
    if (value === 0) return { total: 0, contributors: [] };

    const snap = scope.snapshot;
    const ir = snap.derived?.imperial_rent;
    const territory = snap.territories.find((t) => t.id === scope.this!.id);
    const totalRentLevel = snap.territories.reduce((s, t) => s + t.rent_level, 0);
    const share = territory && totalRentLevel > 0 ? territory.rent_level / totalRentLevel : 0;
    const irTotal = ir?.total ?? 0;

    const contributors: Contributor[] = [
      buildRentContributor(
        "Unequal Exchange",
        ir?.unequal_exchange ?? 0,
        irTotal,
        share,
        "derived.imperial_rent.unequal_exchange",
      ),
      buildRentContributor(
        "Externalized Reproductive",
        ir?.externalized_reproductive ?? 0,
        irTotal,
        share,
        "derived.imperial_rent.externalized_reproductive",
      ),
      buildRentContributor(
        "Domestic Shadow",
        ir?.domestic_shadow ?? 0,
        irTotal,
        share,
        "derived.imperial_rent.domestic_shadow",
      ),
    ];

    return { total: value, contributors };
  },
};

// ---------------------------------------------------------------------------
// org.effective_cadre — base cadre × (1 - heat × penalty)
// ---------------------------------------------------------------------------

const orgEffectiveCadre: ScriptValue = {
  name: "org.effective_cadre",
  label: "Effective Cadre",
  description:
    "Cadre level adjusted for heat penalty. High heat reduces organizational effectiveness.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const org = scope.snapshot.organizations.find((o) => o.id === scope.this!.id);
    if (!org) return 0;

    const baseCadre = org.cadre_level;
    const heatPenalty = org.heat * GAMEDEFINES.HEAT_CADRE_PENALTY;
    return Math.max(0, baseCadre * (1 - heatPenalty));
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgEffectiveCadre.evaluate(scope);
    if (!scope.this || scope.this.kind !== "org") return { total: 0, contributors: [] };

    const org = scope.snapshot.organizations.find((o) => o.id === scope.this!.id);
    if (!org) return { total: 0, contributors: [] };

    const baseCadre = org.cadre_level;
    const heatPenalty = org.heat * GAMEDEFINES.HEAT_CADRE_PENALTY;
    const penaltyValue = baseCadre * heatPenalty;

    const contributors: Contributor[] = [
      {
        label: "Base Cadre",
        value: baseCadre,
        share: value > 0 ? baseCadre / (baseCadre + penaltyValue) : 1,
        source: {
          kind: "snapshot_field",
          path: `organizations[${scope.this.id}].cadre_level`,
        },
        children: [],
      },
      {
        label: "Heat Penalty",
        value: -penaltyValue,
        share: value > 0 ? -penaltyValue / (baseCadre + penaltyValue) : 0,
        source: { kind: "gamedefines", path: "GAMEDEFINES.HEAT_CADRE_PENALTY" },
        children: [
          {
            label: "Organization Heat",
            value: org.heat,
            share: 1,
            source: {
              kind: "snapshot_field",
              path: `organizations[${scope.this.id}].heat`,
            },
            children: [],
          },
        ],
      },
    ];

    return { total: value, contributors };
  },
};

// ---------------------------------------------------------------------------
// org.consciousness_gap — gap between material position and consciousness
// ---------------------------------------------------------------------------

const orgConsciousnessGap: ScriptValue = {
  name: "org.consciousness_gap",
  label: "Consciousness Gap",
  description:
    "Difference between material-conditions proxy (agitation) and actual revolutionary consciousness. Positive = undertapped potential.",
  scopeKind: "org",
  evaluate: (scope: Scope): number => {
    if (!scope.this || scope.this.kind !== "org") return 0;
    const snap = scope.snapshot;
    const org = snap.organizations.find((o) => o.id === scope.this!.id);
    if (!org) return 0;

    // Material position proxy: average agitation across org's territories
    const orgTerritories = snap.territories.filter((t) => org.territory_ids.includes(t.id));
    const avgHeat =
      orgTerritories.length > 0
        ? orgTerritories.reduce((s, t) => s + t.heat, 0) / orgTerritories.length
        : 0;

    // Actual revolutionary consciousness (null until the engine computes it)
    const revConsciousness = org.consciousness?.revolutionary ?? 0;

    return avgHeat - revConsciousness;
  },
  breakdown: (scope: Scope): Breakdown => {
    const value = orgConsciousnessGap.evaluate(scope);
    if (!scope.this || scope.this.kind !== "org") return { total: 0, contributors: [] };

    const snap = scope.snapshot;
    const org = snap.organizations.find((o) => o.id === scope.this!.id);
    if (!org) return { total: 0, contributors: [] };

    const orgTerritories = snap.territories.filter((t) => org.territory_ids.includes(t.id));
    const avgHeat =
      orgTerritories.length > 0
        ? orgTerritories.reduce((s, t) => s + t.heat, 0) / orgTerritories.length
        : 0;
    const revConsciousness = org.consciousness?.revolutionary ?? 0;

    const contributors: Contributor[] = [
      {
        label: "Material Agitation (Avg Territory Heat)",
        value: avgHeat,
        share: Math.abs(value) > 0 ? avgHeat / Math.abs(value) : 0.5,
        source: { kind: "derived", path: "avg(territories[org.territory_ids].heat)" },
        children: orgTerritories.map((t) => ({
          label: t.name,
          value: t.heat,
          share: orgTerritories.length > 0 ? 1 / orgTerritories.length : 0,
          source: { kind: "snapshot_field" as const, path: `territories[${t.id}].heat` },
          children: [],
        })),
      },
      {
        label: "Revolutionary Consciousness",
        value: -revConsciousness,
        share: Math.abs(value) > 0 ? -revConsciousness / Math.abs(value) : -0.5,
        source: {
          kind: "snapshot_field",
          path: `organizations[${scope.this.id}].consciousness.revolutionary`,
        },
        children: [],
      },
    ];

    return { total: value, contributors };
  },
};

// ---------------------------------------------------------------------------
// Register all derived selectors
// ---------------------------------------------------------------------------

selectors.register(hexImperialRent);
selectors.register(orgEffectiveCadre);
selectors.register(orgConsciousnessGap);
