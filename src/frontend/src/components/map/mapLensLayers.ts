/**
 * mapLensLayers.ts — pure layer-descriptor builder for the map lens set.
 *
 * Adapted (spec-110 B2) to the unified `Lens` discriminated union
 * (`@/lib/lens`): callers now pass `lens: Lens` instead of a bare
 * `lensMode: LensMode` string. The five spec-070/093 political-topology
 * modes (stance/heat/habitability/faction/collapse) behave exactly as
 * before; a new `{ kind: "metric"; metric }` case fills territories from a
 * generic per-territory metric bag (`LensTerritory.metrics`), covering the
 * remaining `web/game/map_contract.py` `MAP_METRIC_PROPERTIES` this lens set
 * didn't previously expose (profit_rate, exploitation_rate, occ,
 * imperial_rent, org_presence, population).
 *
 * Extracted as a pure function of (territories, balkanization block, lens)
 * so it's unit-testable without deck.gl/WebGL. `DeckGLMap.tsx` composes the
 * returned descriptor (fill-color function, concentric rings, sovereign
 * CLAIMS hulls, legend text) into real deck.gl layers alongside its
 * existing base hex layer.
 *
 * Color encoding reuses the ratified Cold Collapse tokens (spec-090,
 * `index.css`) rather than inventing new hex literals: UPHOLD -> LASER
 * (#ff3344, "Blood"), IGNORE -> CADRE (#6b8fb5, "Blue"), ABOLISH ->
 * SOLIDARITY (#5fbf7a, "Phosphor"). These are the exact values
 * `design/mockups/themap/map-data.jsx`'s STANCE palette already used.
 *
 * Constitution VIII.9 (binding): community/hyperedge relationships must
 * NEVER render as a spatial hull on the geographic map. This module's hull
 * builder (`buildClaimsHulls`) reads ONLY `BalkanizationBlock.sovereigns[].
 * claimed_territory_ids` — a Sovereign -> Territory CLAIMS relationship
 * (geographic/political axis) — and has no code path that reads a
 * `hyperedges`/`communities`/`HyperedgeState` field, present or not. See
 * `mapLensLayers.test.ts`'s VIII.9 test for the enforced guarantee.
 */

import {
  lensLegendLabel,
  lensRampStops,
  sampleRampStops,
  type Lens,
  type MapMetric,
} from "@/lib/lens";
import { DATA_RAMPS, type RGBAColor } from "@/theme/colors";

// ---------------------------------------------------------------------------
// Types (mirror specs/093-territory-org-detail/contracts/map-balkanization.yaml)
// ---------------------------------------------------------------------------

export type ColonialStance = "UPHOLD" | "IGNORE" | "ABOLISH";

export interface FactionSummary {
  id: string;
  /**
   * Raw wire value — real engine data is the `ColonialStance` StrEnum's
   * lowercase `.value` (`"uphold"`); some fixtures use uppercase display
   * form. Always resolve via `normalizeStance()`, never compare directly.
   */
  colonial_stance: string;
  is_settler_formation?: boolean;
}

export interface SovereignSummary {
  id: string;
  ruling_faction_id: string;
  extraction_policy?: string;
  legitimacy: number;
  /** Sourced from `query_sovereign_claims` — used to build CLAIMS hulls. */
  claimed_territory_ids: string[];
}

export interface FactionInfluenceRow {
  faction_id: string;
  influence_level: number;
  support_type: string;
}

export interface TerritoryInfluence {
  territory_id: string;
  /** Influence rows, descending by influence_level. */
  influences: FactionInfluenceRow[];
  dominant_faction_id: string | null;
  current_sovereign_id: string | null;
  contested: boolean;
  habitability: number;
}

/** The map-snapshot balkanization extension. NEVER carries hyperedge/community data. */
export interface BalkanizationBlock {
  factions: FactionSummary[];
  sovereigns: SovereignSummary[];
  territory_influence: TerritoryInfluence[];
}

/** Minimal territory shape this module needs (subset of TerritoryState). */
export interface LensTerritory {
  id: string;
  h3_index: string | null;
  /**
   * `null` ONLY arises from a RADAR LOOP replay override (Program 17 Wave
   * 3, `DeckGLMap.tsx`'s `territoryToLensTerritory`) when the active
   * frame's window has no recorded value for this territory's county —
   * honest no-data (Constitution III.11), never fabricated. A live
   * (non-replay) merge always supplies a real `TerritoryState.heat`
   * number.
   */
  heat: number | null;
  biocapacity: number;
  max_biocapacity: number;
  /**
   * Real MetabolismSystem habitability (spec-109 A2), when the bridge had a
   * live graph to read it from. `null`/`undefined` falls through to the
   * balkanization-row proxy, then the biocapacity ratio (see
   * `habitabilityFill`) — never fabricated here.
   */
  habitability?: number | null;
  /**
   * The remaining `MAP_METRIC_PROPERTIES` contract values (spec-110 B2's
   * lens-union addition) — one numeric property per `MapMetric`, mirroring
   * what a real `/map/` hex feature's `properties` bag carries. Absent
   * (`undefined`)/missing keys mean "no data for this metric on this
   * territory" (Constitution III.11: loud no-data, never a fabricated 0).
   */
  metrics?: Partial<Record<MapMetric, number>>;
  /**
   * Spec-113 Lane D's `dominant_class` `/map/` property (population-weighted
   * majority `SocialRole` among the territory's TENANCY-linked members) —
   * categorical, so it lives outside the numeric `metrics` bag. `null`/
   * absent means no TENANCY-linked members were present this tick
   * (Constitution III.11: loud no-data, never a fabricated role).
   */
  dominantClass?: string | null;
  /**
   * Wave 2 Round 2's `territory_type` `/map/` property — the real
   * `TerritoryType` enum's `.value` (`src/babylon/models/enums/
   * territory.py`: core/periphery/reservation/penal_colony/
   * concentration_camp), NOT `stub_bridge.py`'s legacy
   * `"URBAN"/"SUBURBAN"/"PERIURBAN"` vocabulary. Categorical, so it lives
   * outside the numeric `metrics` bag, like `dominantClass`. `null`/absent
   * is honest no-data (Constitution III.11), never a fabricated type.
   */
  territoryType?: string | null;
}

export interface RingSpec {
  territoryId: string;
  /** Ring radius scale: 1.0 outer (dominant) / 0.62 mid / 0.30 inner. */
  scale: number;
  color: RGBAColor;
}

export interface HullSpec {
  sovereignId: string;
  color: RGBAColor;
  /** Territory IDs claimed by this sovereign (geometry resolved by the caller). */
  territoryIds: string[];
}

export interface LensLayerResult {
  getFillColor: (territoryId: string) => RGBAColor;
  rings: RingSpec[];
  hulls: HullSpec[];
  legendLabel: string;
}

export interface BuildLensLayersInput {
  territories: LensTerritory[];
  balkanization: BalkanizationBlock | null | undefined;
  lens: Lens;
  factionFilter?: string | null;
}

// ---------------------------------------------------------------------------
// Color tokens (Cold Collapse canon, spec-090 index.css — see module docstring)
// ---------------------------------------------------------------------------

/** Exported (spec-113 Lane B) so `lib/lenses/registry.ts` can build the stance/faction/collapse
 * categorical `MapLensDef.legend` from the SAME tokens this module fills with — one source of
 * truth for "what color is UPHOLD", never a second hardcoded copy in the legend. */
export const STANCE_COLOR: Record<ColonialStance, RGBAColor> = {
  UPHOLD: [255, 51, 68, 220], // --babylon-laser
  IGNORE: [107, 143, 181, 220], // --babylon-cadre
  ABOLISH: [95, 191, 122, 220], // --babylon-solidarity
};

/**
 * The 8 `SocialRole` values (`src/babylon/models/enums/social.py`) the
 * `class_composition` lens fills by — spec-113 Lane B/D. A first-pass
 * categorical palette (not yet colorblind-simulator-verified — DESIGN_BIBLE.md
 * §3.2/§10 flags that QA pass as a standing follow-on for every categorical
 * lens): distinct hues drawn from existing Cold Collapse ramp terminals so no
 * new raw hex literals are invented here.
 */
export const SOCIAL_ROLE_COLOR: Record<string, RGBAColor> = {
  core_bourgeoisie: [212, 160, 44, 220], // wealth ramp terminal — the ruling core class
  labor_aristocracy: [138, 106, 42, 220], // wealth ramp mid-tone — privileged core worker
  comprador_bourgeoisie: [184, 50, 31, 220], // rent ramp terminal — extraction's local agent
  petty_bourgeoisie: [107, 143, 181, 220], // --babylon-cadre
  periphery_proletariat: [77, 217, 230, 220], // --babylon-spire — the exploited producer
  internal_proletariat: [90, 79, 149, 220], // population ramp mid-tone
  lumpenproletariat: [122, 53, 37, 220], // biocapacity ramp's depleted-red neighbor
  carceral_enforcer: [255, 51, 68, 220], // --babylon-laser — the repressive apparatus
};

/** Display labels for `SOCIAL_ROLE_COLOR`'s keys — shared by the categorical legend. */
export const SOCIAL_ROLE_LABELS: Record<string, string> = {
  core_bourgeoisie: "Core Bourgeoisie",
  labor_aristocracy: "Labor Aristocracy",
  comprador_bourgeoisie: "Comprador Bourgeoisie",
  petty_bourgeoisie: "Petty Bourgeoisie",
  periphery_proletariat: "Periphery Proletariat",
  internal_proletariat: "Internal Proletariat",
  lumpenproletariat: "Lumpenproletariat",
  carceral_enforcer: "Carceral Enforcer",
};

/**
 * The 5 real `TerritoryType` enum values (`src/babylon/models/enums/
 * territory.py`, snake_case `.value` wire form — CORE/PERIPHERY/RESERVATION/
 * PENAL_COLONY/CONCENTRATION_CAMP; NOT `stub_bridge.py`'s legacy
 * `"URBAN"/"SUBURBAN"/"PERIURBAN"` vocabulary) — Wave 2 Round 2's
 * `territory_type` lens, per the settler-colonial territorial hierarchy the
 * enum's own docstring describes. Palette direction per DESIGN_BIBLE.md §9b
 * (Percy's binding ksbc ruling, crimson/gold on near-black): CORE gets the
 * ksbc chrome accent-gold (`#ffd700` — "wealth/privilege"); PERIPHERY gets
 * the Cold Collapse heat-ramp's `#d97a2c` terminal (the enum's own docstring
 * calls periphery "high heat"); the Necropolitical Triad
 * (RESERVATION/PENAL_COLONY/CONCENTRATION_CAMP) escalates through the rent
 * ramp's "extraction → violence" tones into `--babylon-laser` — no new raw
 * hex literals invented (same discipline as `SOCIAL_ROLE_COLOR`).
 */
export const TERRITORY_TYPE_COLOR: Record<string, RGBAColor> = {
  core: [255, 215, 0, 220], // ksbc accent-gold #ffd700 — labor-aristocracy destination
  periphery: [217, 122, 44, 220], // --babylon-heat #d97a2c — "low value, high heat"
  reservation: [86, 53, 107, 220], // rent ramp mid-tone #56356b — administrative containment
  penal_colony: [168, 58, 120, 220], // rent ramp #a83a78 — extraction intensifies
  concentration_camp: [255, 51, 68, 220], // --babylon-laser #ff3344 — necropolitical endpoint
};

/** Display labels for `TERRITORY_TYPE_COLOR`'s keys — shared by the categorical legend. */
export const TERRITORY_TYPE_LABELS: Record<string, string> = {
  core: "Core",
  periphery: "Periphery",
  reservation: "Reservation",
  penal_colony: "Penal Colony",
  concentration_camp: "Concentration Camp",
};

const DESATURATED: RGBAColor = [26, 31, 42, 140]; // low-influence dim tone
const NO_DATA: RGBAColor = [58, 53, 48, 160];

const RING_SCALES = [1.0, 0.62, 0.3] as const;
const MEANINGFUL_INFLUENCE_THRESHOLD = 0.2;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function influenceRowsFor(
  territoryId: string,
  balkanization: BalkanizationBlock | null | undefined,
): FactionInfluenceRow[] {
  return (
    balkanization?.territory_influence.find((t) => t.territory_id === territoryId)?.influences ?? []
  );
}

/**
 * Normalize a `colonial_stance` value to its canonical uppercase form.
 *
 * The backend's `_build_balkanization_block` (`web/game/engine_bridge.py`)
 * passes through the raw graph attribute verbatim, which — for real
 * engine-computed data — is the `ColonialStance` StrEnum's lowercase
 * `.value` (`"uphold"`/`"ignore"`/`"abolish"`, `src/babylon/models/enums/
 * balkanization.py:49-51`), not the uppercase form the mockup/contract
 * doc use for display. Normalizing here (rather than assuming one casing)
 * keeps this module correct against both real engine data and any
 * uppercase test/dev fixtures.
 */
function normalizeStance(value: string): ColonialStance | null {
  const upper = value.toUpperCase();
  return upper === "UPHOLD" || upper === "IGNORE" || upper === "ABOLISH"
    ? (upper as ColonialStance)
    : null;
}

/** Exported (spec-113 Lane B) so `DeckGLMap.tsx` can color political CLAIMS layer fills by
 * the SAME per-faction stance a sovereign's ruling faction resolves to elsewhere in this
 * module (`buildClaimsHulls`) — one source of truth, not a second copy of this lookup. */
export function factionStance(
  factionId: string | null | undefined,
  balkanization: BalkanizationBlock | null | undefined,
): ColonialStance | null {
  if (!factionId) return null;
  const raw = balkanization?.factions.find((f) => f.id === factionId)?.colonial_stance;
  return raw ? normalizeStance(raw) : null;
}

// ---------------------------------------------------------------------------
// Per-lens fill-color builders
// ---------------------------------------------------------------------------

function stanceFill(
  territoryId: string,
  balkanization: BalkanizationBlock | null | undefined,
): RGBAColor {
  const rows = influenceRowsFor(territoryId, balkanization);
  if (rows.length === 0) return NO_DATA;
  const dominant = rows[0];
  const stance = factionStance(dominant?.faction_id, balkanization);
  if (!stance) return NO_DATA;
  const base = STANCE_COLOR[stance];
  const opacity = Math.round(
    lerp(70, 230, Math.max(0, Math.min(1, dominant?.influence_level ?? 0))),
  );
  return [base[0], base[1], base[2], opacity];
}

function heatFill(territory: LensTerritory): RGBAColor {
  // territory.heat is null only under an active RADAR LOOP replay override
  // for a county the current frame carries no reading for — honest NO_DATA
  // (Constitution III.11), never a fabricated ramp-floor color.
  if (territory.heat === null) return NO_DATA;
  return sampleRampStops(DATA_RAMPS.heat, territory.heat);
}

function habitabilityFill(
  territoryId: string,
  territory: LensTerritory,
  balkanization: BalkanizationBlock | null | undefined,
): RGBAColor {
  const row = balkanization?.territory_influence.find((t) => t.territory_id === territoryId);
  // Spec-109 A2: prefer the territory's own real habitability (read live off
  // the graph by the bridge) over the balkanization row's derived value,
  // falling back to the biocapacity ratio only when neither is available.
  const habitability =
    territory.habitability ??
    row?.habitability ??
    territory.biocapacity / (territory.max_biocapacity || 1);
  // Diverging: low (crimson) <-> high (green). Reuse the biocapacity ramp.
  return sampleRampStops(DATA_RAMPS.biocapacity, habitability);
}

function factionFill(
  territoryId: string,
  balkanization: BalkanizationBlock | null | undefined,
  factionFilter: string | null | undefined,
): RGBAColor {
  if (!factionFilter) return NO_DATA;
  const rows = influenceRowsFor(territoryId, balkanization);
  const row = rows.find((r) => r.faction_id === factionFilter);
  const level = row?.influence_level ?? 0;
  if (level < MEANINGFUL_INFLUENCE_THRESHOLD) return DESATURATED;
  const stance = factionStance(factionFilter, balkanization);
  if (!stance) return DESATURATED;
  const base = STANCE_COLOR[stance];
  const opacity = Math.round(lerp(70, 230, level));
  return [base[0], base[1], base[2], opacity];
}

function collapseFill(
  territoryId: string,
  balkanization: BalkanizationBlock | null | undefined,
): RGBAColor {
  const rows = influenceRowsFor(territoryId, balkanization);
  if (rows.length === 0) return NO_DATA;
  const row = balkanization?.territory_influence.find((t) => t.territory_id === territoryId);
  if (row?.contested) {
    return [255, 180, 50, 220];
  }
  return stanceFill(territoryId, balkanization);
}

/**
 * Metric-kind fill (the B2 lens-union addition): samples the metric's ramp
 * at the territory's `metrics[metric]` value. Missing data (no `metrics`
 * bag, or the specific metric absent) is a loud NO_DATA fill, not a
 * fabricated 0 (Constitution III.11 — an empty domain is not a failure,
 * but it must render as visibly distinct from a real 0.0).
 */
function metricFill(territory: LensTerritory | undefined, metric: MapMetric): RGBAColor {
  const value = territory?.metrics?.[metric];
  if (value === undefined) return NO_DATA;
  const stops = lensRampStops({ kind: "metric", metric });
  if (!stops) return NO_DATA;
  return sampleRampStops(stops, value);
}

/**
 * `class_composition` fill (spec-113 Lane B/D): the territory's own
 * `dominantClass` `SocialRole`, colored via `SOCIAL_ROLE_COLOR`. Loud
 * no-data (Constitution III.11) for an absent/unrecognized role, never a
 * fabricated color.
 */
function classCompositionFill(territory: LensTerritory | undefined): RGBAColor {
  const role = territory?.dominantClass;
  if (!role) return NO_DATA;
  return SOCIAL_ROLE_COLOR[role] ?? NO_DATA;
}

/**
 * `territory_type` fill (Wave 2 Round 2): the territory's own
 * `territoryType` (real `TerritoryType` enum value), colored via
 * `TERRITORY_TYPE_COLOR`. Loud no-data (Constitution III.11) for an
 * absent/unrecognized value, never a fabricated color — mirrors
 * `classCompositionFill` exactly.
 */
function territoryTypeFill(territory: LensTerritory | undefined): RGBAColor {
  const type = territory?.territoryType;
  if (!type) return NO_DATA;
  return TERRITORY_TYPE_COLOR[type] ?? NO_DATA;
}

// ---------------------------------------------------------------------------
// Rings + hulls
// ---------------------------------------------------------------------------

function buildRings(
  territories: LensTerritory[],
  balkanization: BalkanizationBlock | null | undefined,
): RingSpec[] {
  const rings: RingSpec[] = [];
  for (const territory of territories) {
    const rows = influenceRowsFor(territory.id, balkanization);
    // Secondary/tertiary rings — one entry per non-dominant influence row,
    // scaled by RING_SCALES[1]/[2] (matches map-canvas.jsx's RING_SCALES).
    for (let i = 1; i < rows.length && i < RING_SCALES.length; i++) {
      const row = rows[i];
      if (!row) continue;
      const stance = factionStance(row.faction_id, balkanization);
      if (!stance) continue;
      const base = STANCE_COLOR[stance];
      const opacity = Math.round(lerp(30, 180, row.influence_level));
      rings.push({
        territoryId: territory.id,
        scale: RING_SCALES[i] ?? 0.3,
        color: [base[0], base[1], base[2], opacity],
      });
    }
  }
  return rings;
}

/**
 * Build sovereign CLAIMS hull descriptors. Reads ONLY
 * `sovereigns[].claimed_territory_ids` (Sovereign->Territory CLAIMS edges) —
 * never hyperedge/community membership (Constitution VIII.9).
 */
function buildClaimsHulls(balkanization: BalkanizationBlock | null | undefined): HullSpec[] {
  if (!balkanization) return [];
  const hulls: HullSpec[] = [];
  for (const sovereign of balkanization.sovereigns) {
    if (sovereign.claimed_territory_ids.length === 0) continue;
    const stance = factionStance(sovereign.ruling_faction_id, balkanization);
    const color: RGBAColor = stance ? STANCE_COLOR[stance] : [200, 168, 96, 200];
    hulls.push({
      sovereignId: sovereign.id,
      color,
      territoryIds: [...sovereign.claimed_territory_ids].sort(),
    });
  }
  return hulls;
}

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

/** Lens modes that render concentric influence rings + sovereign CLAIMS hulls. */
const RING_AND_HULL_KINDS: ReadonlySet<string> = new Set(["stance", "collapse"]);

/**
 * Lens kinds whose fill derives entirely from the balkanization block.
 * Heat/habitability are territory-local (heat; biocapacity fallback) and
 * metric lenses read the territory's own `metrics` bag — none of these must
 * be blanked when the faction layer is unseeded — the loud no-data state
 * (Constitution III.11) stays per-territory for them instead.
 */
export const BALKANIZATION_LENSES: ReadonlySet<string> = new Set(["stance", "faction", "collapse"]);

function isBalkanizationEmpty(b: BalkanizationBlock): boolean {
  return b.factions.length === 0 && b.sovereigns.length === 0 && b.territory_influence.length === 0;
}

export function buildLensLayers(input: BuildLensLayersInput): LensLayerResult {
  const { territories, balkanization, lens, factionFilter } = input;
  const legendLabel = lensLegendLabel(lens);

  if (
    (!balkanization || isBalkanizationEmpty(balkanization)) &&
    BALKANIZATION_LENSES.has(lens.kind)
  ) {
    return {
      getFillColor: () => NO_DATA,
      rings: [],
      hulls: [],
      legendLabel: `${legendLabel} — no data`,
    };
  }

  const getFillColor = (territoryId: string): RGBAColor => {
    const territory = territories.find((t) => t.id === territoryId);
    switch (lens.kind) {
      case "stance":
        return stanceFill(territoryId, balkanization);
      case "heat":
        return territory ? heatFill(territory) : NO_DATA;
      case "habitability":
        return territory ? habitabilityFill(territoryId, territory, balkanization) : NO_DATA;
      case "faction":
        return factionFill(territoryId, balkanization, factionFilter);
      case "collapse":
        return collapseFill(territoryId, balkanization);
      case "metric":
        return metricFill(territory, lens.metric);
      case "class_composition":
        return classCompositionFill(territory);
      case "territory_type":
        return territoryTypeFill(territory);
      case "field_flow":
        // Wave 3 §11's gradient-wind vector lens: the wind rides ABOVE the
        // base map (components/map/layers/fieldFlow.ts), so the hex fill
        // underneath is just a neutral/dim backdrop — reuses the same
        // low-influence dim tone the faction lens desaturates unmeaningful
        // territories to, never a fabricated ramp (there is no ramp; see
        // lib/lens.ts's lensRampStops).
        return DESATURATED;
    }
  };

  const showRingsAndHulls = RING_AND_HULL_KINDS.has(lens.kind);

  return {
    getFillColor,
    rings: showRingsAndHulls ? buildRings(territories, balkanization) : [],
    hulls: showRingsAndHulls ? buildClaimsHulls(balkanization) : [],
    legendLabel,
  };
}
