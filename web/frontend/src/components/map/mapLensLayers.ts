/**
 * mapLensLayers.ts — pure layer-descriptor builder for the spec-070
 * political-topology map lens set (stance / heat / habitability / faction /
 * collapse).
 *
 * Extracted as a pure function of (territories, balkanization block, lens
 * mode) so it's unit-testable without deck.gl/WebGL. `DeckGLMap.tsx`
 * composes the returned descriptor (fill-color function, concentric rings,
 * sovereign CLAIMS hulls, legend text) into real deck.gl layers alongside
 * its existing base hex layer.
 *
 * Color encoding reuses the ratified Cold Collapse tokens (spec-090,
 * `web/frontend/src/index.css`) rather than inventing new hex literals:
 * UPHOLD -> LASER (#ff3344, "Blood"), IGNORE -> CADRE (#6b8fb5, "Blue"),
 * ABOLISH -> SOLIDARITY (#5fbf7a, "Phosphor"). These are the exact values
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

import type { RGBAColor } from "@/theme/colors";
import { rampForLayer } from "@/theme/colors";

// ---------------------------------------------------------------------------
// Types (mirror specs/093-territory-org-detail/contracts/map-balkanization.yaml)
// ---------------------------------------------------------------------------

export type LensMode = "stance" | "heat" | "habitability" | "faction" | "collapse";

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
  heat: number;
  biocapacity: number;
  max_biocapacity: number;
  /**
   * Real MetabolismSystem habitability (spec-109 A2), when the bridge had a
   * live graph to read it from. `null`/`undefined` falls through to the
   * balkanization-row proxy, then the biocapacity ratio (see
   * `habitabilityFill`) — never fabricated here.
   */
  habitability?: number | null;
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
  lensMode: LensMode;
  factionFilter?: string | null;
}

// ---------------------------------------------------------------------------
// Color tokens (Cold Collapse canon, spec-090 index.css — see module docstring)
// ---------------------------------------------------------------------------

const STANCE_COLOR: Record<ColonialStance, RGBAColor> = {
  UPHOLD: [255, 51, 68, 220], // --babylon-laser
  IGNORE: [107, 143, 181, 220], // --babylon-cadre
  ABOLISH: [95, 191, 122, 220], // --babylon-solidarity
};

const DESATURATED: RGBAColor = [26, 31, 42, 140]; // low-influence dim tone
const NO_DATA: RGBAColor = [58, 53, 48, 160];

const RING_SCALES = [1.0, 0.62, 0.3] as const;
const MEANINGFUL_INFLUENCE_THRESHOLD = 0.2;

function hexToRgba(hex: string, alpha: number): RGBAColor {
  const h = hex.replace(/^#/, "");
  const num = parseInt(h, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255, alpha];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Sample a hex-stop ramp (from `theme/colors.ts`) at normalized t in [0,1]. */
function sampleRamp(stops: string[], t: number, alpha = 220): RGBAColor {
  const clamped = Math.max(0, Math.min(1, t));
  const seg = clamped * (stops.length - 1);
  const i = Math.min(Math.floor(seg), stops.length - 2);
  const f = seg - i;
  const a = hexToRgba(stops[i] ?? "#000000", alpha);
  const b = hexToRgba(stops[i + 1] ?? "#000000", alpha);
  return [
    Math.round(lerp(a[0], b[0], f)),
    Math.round(lerp(a[1], b[1], f)),
    Math.round(lerp(a[2], b[2], f)),
    alpha,
  ];
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

function factionStance(
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
  return sampleRamp(rampForLayer("heat"), territory.heat);
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
  return sampleRamp(rampForLayer("biocapacity"), habitability);
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
// Legend text per lens
// ---------------------------------------------------------------------------

const LEGEND_LABELS: Record<LensMode, string> = {
  stance: "Colonial Stance · Influence",
  heat: "Heat · State Attention",
  habitability: "Habitability · Metabolic Rift",
  faction: "Faction Filter · Influence",
  collapse: "Collapse Moment · Territory Transitions",
};

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

/** Lens modes that render concentric influence rings + sovereign CLAIMS hulls. */
const RING_AND_HULL_LENSES: ReadonlySet<LensMode> = new Set(["stance", "collapse"]);

/**
 * Lens modes whose fill derives entirely from the balkanization block.
 * Heat/habitability are territory-local (heat; biocapacity fallback) and must
 * NOT be blanked when the faction layer is unseeded — the loud no-data state
 * (Constitution III.11) stays per-territory for them instead.
 */
export const BALKANIZATION_LENSES: ReadonlySet<LensMode> = new Set([
  "stance",
  "faction",
  "collapse",
]);

function isBalkanizationEmpty(b: BalkanizationBlock): boolean {
  return b.factions.length === 0 && b.sovereigns.length === 0 && b.territory_influence.length === 0;
}

export function buildLensLayers(input: BuildLensLayersInput): LensLayerResult {
  const { territories, balkanization, lensMode, factionFilter } = input;

  if (
    (!balkanization || isBalkanizationEmpty(balkanization)) &&
    BALKANIZATION_LENSES.has(lensMode)
  ) {
    return {
      getFillColor: () => NO_DATA,
      rings: [],
      hulls: [],
      legendLabel: `${LEGEND_LABELS[lensMode]} — no data`,
    };
  }

  const getFillColor = (territoryId: string): RGBAColor => {
    const territory = territories.find((t) => t.id === territoryId);
    switch (lensMode) {
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
    }
  };

  const showRingsAndHulls = RING_AND_HULL_LENSES.has(lensMode);

  return {
    getFillColor,
    rings: showRingsAndHulls ? buildRings(territories, balkanization) : [],
    hulls: showRingsAndHulls ? buildClaimsHulls(balkanization) : [],
    legendLabel: LEGEND_LABELS[lensMode],
  };
}
