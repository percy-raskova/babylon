/**
 * deck.gl + MapLibre political-cartography map (spec-113 Lane B rewrite of
 * the spec-112 C5 hex/region map).
 *
 * Adapted (spec-110 B2) to the unified `Lens` discriminated union
 * (`@/lib/lens`) and decoupled from both `mapStore` (stores are B3
 * territory) and `react-router` (routing is B3 territory): this is a
 * controlled component — the active lens, faction filter, framing, and
 * territory click all come in via props/callbacks instead of zustand state
 * and `useNavigate`.
 *
 * Spec-113 §7/DESIGN_BIBLE.md §2: the political cartography layer stack
 * (`layers/political.ts`, Lane Carto's frozen export) is now the map's base
 * — de jure county hairlines + state borders, de facto polity fills/claim
 * borders — drawn UNDER the active lens's hex/region fill at every framing
 * ("de-jure hairlines + state borders ALWAYS on"). Controls (lens bar,
 * legend, framing selector) are extracted to `MapControls.tsx` (architecture
 * §3.3) — this component is pure canvas + tooltips + the political/lens
 * layer composition.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { DeckGL } from "@deck.gl/react";
import { H3HexagonLayer, H3ClusterLayer } from "@deck.gl/geo-layers";
import { PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
// Aliased: an unaliased `Map` import shadows the global `Map` constructor
// for the rest of this module, which this file now uses (`fipsByTerritoryId`,
// `hexFeaturesByH3`'s fallback) — a latent collision the pre-Lane-B version
// never tripped because it never called `new Map(...)` anywhere.
import { Map as MapLibreMap } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import type { RGBAColor } from "@/theme/colors";

import { MapControls } from "@/components/map/MapControls";
import { HexTooltip } from "@/components/map/HexTooltip";
import {
  BALKANIZATION_LENSES,
  buildLensLayers,
  factionStance,
  STANCE_COLOR,
  type BalkanizationBlock,
  type LensTerritory,
  type RingSpec,
  type HullSpec,
} from "@/components/map/mapLensLayers";
import { hullPolygonForTerritories } from "@/components/map/mapLensGeometry";
import { buildPoliticalLayers, type PolityClaim } from "@/components/map/layers/political";
import {
  loadCountyTopology,
  loadStateTopology,
  countyFeatures,
  stateFeatures,
  type CountyTopology,
  type StateTopology,
} from "@/lib/geo/topology";
import { regionFillForLens, type FillDomain, type RegionFillProperties } from "@/lib/regionFill";
import {
  hexFeaturePropertiesByH3,
  availableMetricsFromMapData,
  type HexMapFeatureProperties,
} from "@/lib/mapMetadata";
import { lensKey, type Lens } from "@/lib/lens";
import type {
  AdminFeatureProperties,
  AdminLevel,
  GameSnapshot,
  TerritoryState,
  MapSnapshotMetadata,
} from "@/types/game";
import type { Feature, FeatureCollection } from "geojson";

type H3Territory = TerritoryState & { h3_index: string };

/**
 * An aggregated (non-hex) `/map/` feature — spec-112 C5. Real aggregated
 * features ship `geometry: null` (the backend defers real polygons to the
 * frontend's `H3ClusterLayer`), which the `geojson` package's `Feature`
 * type doesn't express, so `mapData.features` is cast to this through
 * `unknown` at the one call site that builds region layers.
 */
type RegionFeature = Feature & { properties: AdminFeatureProperties };

/** Default fill opacity when the caller doesn't specify one. */
const DEFAULT_LAYER_OPACITY = 0.8;

/** Neutral fill for a region regionFillForLens has no data for — mirrors mapLensLayers.ts's NO_DATA. */
const REGION_NO_DATA_FILL: RGBAColor = [58, 53, 48, 160];
/** Structural gray border between adjacent regions. */
const REGION_LINE_COLOR: RGBAColor = [130, 138, 150, 160];

/**
 * Concentric influence rings (stance/collapse lenses only) — one
 * `H3HexagonLayer` per ring, reusing `coverage` to shrink each hex to the
 * ring's scale (1.0/0.62/0.30), per `map-canvas.jsx`'s `RING_SCALES`.
 */
function buildRingLayers(rings: RingSpec[], h3Territories: H3Territory[]): H3HexagonLayer[] {
  const layers: H3HexagonLayer[] = [];
  for (const ring of rings) {
    const territory = h3Territories.find((t) => t.id === ring.territoryId);
    if (!territory) continue;
    layers.push(
      new H3HexagonLayer({
        id: `lens-ring-${ring.territoryId}-${ring.scale}`,
        data: [territory],
        getHexagon: (t: H3Territory) => t.h3_index,
        getFillColor: () => ring.color,
        coverage: ring.scale,
        getElevation: 0,
        extruded: false,
        pickable: false,
        stroked: false,
      }),
    );
  }
  return layers;
}

/**
 * Sovereign CLAIMS hulls — geographic overlay derived ONLY from
 * `SovereignSummary.claimed_territory_ids` (Constitution VIII.9: never
 * hyperedge/community data).
 */
function buildClaimsHullLayers(hulls: HullSpec[], h3Territories: H3Territory[]): PolygonLayer[] {
  const layers: PolygonLayer[] = [];
  for (const hull of hulls) {
    const polygon = hullPolygonForTerritories(hull.territoryIds, h3Territories);
    if (!polygon) continue;
    layers.push(
      new PolygonLayer({
        id: `claims-hull-${hull.sovereignId}`,
        data: [{ polygon }],
        getPolygon: (d: { polygon: [number, number][] }) => d.polygon,
        getFillColor: [0, 0, 0, 0],
        getLineColor: hull.color,
        lineWidthMinPixels: 2,
        filled: false,
        stroked: true,
        pickable: false,
      }),
    );
  }
  return layers;
}

/** `null` -> `undefined` (the `LensTerritory.metrics` bag's "absent" spelling — see its docstring). */
function nullToUndefined(v: number | null | undefined): number | undefined {
  return v ?? undefined;
}

/** The numeric `metrics` bag `territoryToLensTerritory` merges from one hex feature's properties. */
function hexPropsToMetrics(hexProps: HexMapFeatureProperties): LensTerritory["metrics"] {
  return {
    profit_rate: nullToUndefined(hexProps.profit_rate),
    exploitation_rate: nullToUndefined(hexProps.exploitation_rate),
    occ: nullToUndefined(hexProps.occ),
    imperial_rent: nullToUndefined(hexProps.imperial_rent),
    org_presence: nullToUndefined(hexProps.org_presence),
    population: nullToUndefined(hexProps.population),
    solidarity_index: nullToUndefined(hexProps.solidarity_index),
  };
}

/**
 * Merge one `TerritoryState` with its matching hex-zoom `/map/` feature
 * properties (keyed by `h3_index`, when present) into a `LensTerritory` —
 * `buildLensLayers`'s input shape. Extracted to a pure top-level function
 * (spec-113 Lane B) so `DeckGLMap`'s render body stays a plain `.map()`
 * call instead of an inline multi-branch arrow (cognitive-complexity
 * budget) — also makes the merge independently unit-testable.
 */
function territoryToLensTerritory(
  t: TerritoryState,
  hexFeaturesByH3: Map<string, HexMapFeatureProperties>,
): LensTerritory {
  const hexProps = t.h3_index ? hexFeaturesByH3.get(t.h3_index) : undefined;
  return {
    id: t.id,
    h3_index: t.h3_index,
    heat: t.heat,
    biocapacity: t.biocapacity,
    // Spec-109 A2: real Territory field, was hardcoded to 100.
    max_biocapacity: t.max_biocapacity ?? 100,
    habitability: t.habitability ?? hexProps?.habitability ?? null,
    dominantClass: hexProps?.dominant_class ?? null,
    metrics: hexProps ? hexPropsToMetrics(hexProps) : undefined,
  };
}

/**
 * Real min/max across a lens's domain-normalized field (heat,
 * `{kind:"metric"}`), scanning all region features — a per-render
 * auto-scaled range, since aggregated heat/metric values have no fixed
 * [0, 1] span the way a per-hex value might (see `regionFillForLens`).
 * Lens kinds that don't use a domain get an inert `{min:0,max:1}` default.
 * The RESULT of this "natural" scan is never used directly for region fill
 * or the legend marker — both route through the render-time domain cache
 * first (DESIGN_BIBLE.md §3.2/§6: "no silent rescale between ticks" — see
 * the `domainCache` state in `DeckGLMap` below).
 */
function computeFillDomain(lens: Lens, propertyBags: RegionFillProperties[]): FillDomain {
  let key: keyof RegionFillProperties | null = null;
  if (lens.kind === "heat") {
    key = "heat";
  } else if (lens.kind === "metric") {
    key = lens.metric;
  }
  if (key === null) return { min: 0, max: 1 };
  const values = propertyBags
    .map((p) => p[key])
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (values.length === 0) return { min: 0, max: 1 };
  return { min: Math.min(...values), max: Math.max(...values) };
}

/** Mean of the finite values in `values`, or `null` for an all-absent set (honest no-summary). */
function meanOfFinite(values: (number | null | undefined)[]): number | null {
  const finite = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (finite.length === 0) return null;
  return finite.reduce((a, b) => a + b, 0) / finite.length;
}

/**
 * The legend marker's normalized [0,1] position for the CURRENT world
 * state (DESIGN_BIBLE.md §3.2's Sylvester citation) — `null` for categorical
 * lenses (no ramp to mark) or when no real values are present (Constitution
 * III.11: no marker beats a fabricated one). Habitability is never
 * domain-normalized (its values already live in ~[0,1] — matches
 * `habitabilityFill`/`regionFillForLens`'s own habitability branch); heat
 * and metric lenses normalize by `domain` at region framing and clamp the
 * raw mean directly at hex framing (mirroring how the hex fill itself
 * samples those values — see `mapLensLayers.ts`'s `heatFill`/`metricFill`).
 */
function currentValueForLens(
  lens: Lens,
  framing: AdminLevel,
  hexValues: (number | null | undefined)[],
  regionValues: (number | null | undefined)[],
  domain: FillDomain,
): number | null {
  if (
    lens.kind === "stance" ||
    lens.kind === "faction" ||
    lens.kind === "collapse" ||
    lens.kind === "class_composition"
  ) {
    return null;
  }
  const mean = meanOfFinite(framing === "hex" ? hexValues : regionValues);
  if (mean === null) return null;
  if (lens.kind === "habitability" || framing === "hex") {
    return Math.max(0, Math.min(1, mean));
  }
  const span = domain.max - domain.min;
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (mean - domain.min) / span));
}

/** `currentValueForLens`'s hex-framing raw sample values for `lens` — extracted (cognitive-complexity budget). */
function hexMarkerValuesForLens(
  lens: Lens,
  territories: TerritoryState[],
  hexFeaturesByH3: Map<string, HexMapFeatureProperties>,
): (number | null | undefined)[] {
  if (lens.kind === "heat") return territories.map((t) => t.heat);
  if (lens.kind === "habitability") return territories.map((t) => t.habitability ?? null);
  if (lens.kind === "metric") {
    const metric = lens.metric;
    return territories.map((t) => hexFeaturesByH3.get(t.h3_index ?? "")?.[metric]);
  }
  return [];
}

/** `currentValueForLens`'s region-framing raw sample values for `lens` — extracted (cognitive-complexity budget). */
function regionMarkerValuesForLens(
  lens: Lens,
  regionFeatures: RegionFeature[],
): (number | null | undefined)[] {
  if (lens.kind === "heat") return regionFeatures.map((f) => f.properties.heat);
  if (lens.kind === "habitability") {
    return regionFeatures.map((f) => (f.properties as { habitability?: number }).habitability);
  }
  if (lens.kind === "metric") {
    const metric = lens.metric;
    return regionFeatures.map((f) => (f.properties as unknown as Record<string, number>)[metric]);
  }
  return [];
}

/**
 * Region (county/cz/msa/bea_ea/state) fill layer — spec-112 C5. Reads real
 * polygons from each feature's `properties.member_h3` via `H3ClusterLayer`
 * (h3-js's `cellsToMultiPolygon` internally), since the backend ships
 * `geometry: null` for aggregated features.
 */
function buildRegionLayer(
  features: RegionFeature[],
  lens: Lens,
  domain: FillDomain,
  layerOpacity: number,
): H3ClusterLayer<RegionFeature> {
  return new H3ClusterLayer<RegionFeature>({
    id: "region-clusters",
    data: features,
    getHexagons: (f) => f.properties.member_h3 ?? [],
    getFillColor: (f) => regionFillForLens(lens, f.properties, domain) ?? REGION_NO_DATA_FILL,
    getLineColor: REGION_LINE_COLOR,
    lineWidthMinPixels: 1,
    getElevation: 0,
    extruded: false,
    opacity: layerOpacity,
    pickable: true,
    autoHighlight: true,
    highlightColor: [200, 168, 96, 180],
    updateTriggers: {
      getFillColor: [lens, domain],
    },
  });
}

/**
 * Self-authored minimal MapLibre style (Lane Carto, spec-113 §7) — land/
 * water only, Cold Collapse values. Replaces the Carto Dark Matter tile
 * dependency: the political cartography layer stack IS the map now.
 */
const MAP_STYLE = "/geo/basemap-style.json";

/** Default view centered on Southeast Michigan (the canonical scenario region). */
const INITIAL_VIEW_STATE = {
  longitude: -83.2,
  latitude: 42.5,
  zoom: 8,
  pitch: 30,
  bearing: 0,
};

interface DeckGLMapProps {
  snapshot: GameSnapshot;
  /**
   * The map-snapshot FeatureCollection from `GET /api/games/{id}/map/`
   * (the caller's `mapData`). Spec-093's balkanization block lives under
   * `mapData.metadata.balkanization` — NOT on `GameSnapshot` — see
   * `types/game.ts`'s `MapSnapshotMetadata` docstring. `metadata` isn't a
   * standard GeoJSON `FeatureCollection` field; the backend attaches it as
   * an extra top-level key (`EngineBridge.get_map_snapshot`).
   */
  mapData?: (FeatureCollection & { metadata?: MapSnapshotMetadata }) | null;
  /** The active lens (replaces the old `activeLayer` + `lensMode` pair). */
  lens: Lens;
  /** Called when the user clicks a lens-mode button. Uncontrolled if omitted. */
  onLensChange?: (lens: Lens) => void;
  /** Selected faction for the "faction" lens. */
  factionFilter?: string | null;
  onFactionFilterChange?: (factionId: string | null) => void;
  /** Hex fill opacity [0, 1]. Defaults to 0.8. */
  layerOpacity?: number;
  /** Called on hex click instead of navigating internally (routing is B3's job). */
  onTerritoryClick?: (territoryId: string) => void;
  /**
   * Admin-level spatial aggregation LOD (spec-112 C5). Defaults to "hex" —
   * the pre-county-framing rendered behavior — so every caller that
   * doesn't pass this renders byte-identically to before.
   */
  framing?: AdminLevel;
  /** Called when the user clicks a framing-scale button. Uncontrolled if omitted. */
  onFramingChange?: (level: AdminLevel) => void;
}

/** Discriminates a hex-territory hover from an aggregated-region hover. */
type HoverInfo =
  | { kind: "territory"; territory: TerritoryState; x: number; y: number }
  | { kind: "region"; properties: AdminFeatureProperties; x: number; y: number };

/**
 * Tooltip for hovering an aggregated region — `group_name` plus a handful
 * of real backend aggregates (`AdminFeatureProperties`, `types/game.ts`).
 * Kept local (not a `HexTooltip` variant): `HexTooltip` is tightly typed to
 * `TerritoryState` and its lens-priority metric table doesn't apply to
 * region properties.
 */
function RegionTooltip({
  properties,
  x,
  y,
}: {
  properties: AdminFeatureProperties;
  x: number;
  y: number;
}) {
  return (
    <div
      data-testid="region-tooltip"
      className="pointer-events-none absolute z-50 min-w-[200px] rounded-md border border-wet-steel bg-concrete p-3 text-xs shadow-lg"
      style={{ left: x + 12, top: y + 12 }}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-bone">{properties.group_name}</span>
        <span className="rounded bg-rebar px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-ash">
          {properties.group_level}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <RegionStat label="Hexes" value={properties.hex_count.toLocaleString()} />
        <RegionStat label="Population" value={properties.population.toLocaleString()} />
        <RegionStat label="Heat" value={properties.heat.toFixed(2)} />
        <RegionStat label="Org Presence" value={properties.org_presence.toLocaleString()} />
        <RegionStat label="Profit Rate" value={properties.profit_rate.toFixed(2)} />
        <RegionStat label="Imperial Rent" value={properties.imperial_rent.toFixed(2)} />
      </div>
    </div>
  );
}

function RegionStat({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="text-ash" data-testid="region-tooltip-stat-label">
        {label}
      </span>
      <span className="font-mono text-bone">{value}</span>
    </>
  );
}

/**
 * Resolve a deck.gl hover event into `HoverInfo`, or `null` when hover
 * clears — extracted to a top-level function (spec-113 Lane B,
 * cognitive-complexity budget) so the `<DeckGL onHover>` prop is a
 * one-line call.
 */
function resolveHoverInfo(
  info: { object?: unknown; x: number; y: number },
  framing: AdminLevel,
): HoverInfo | null {
  if (!info.object) return null;
  if (framing !== "hex") {
    const feature = info.object as RegionFeature;
    return { kind: "region", properties: feature.properties, x: info.x, y: info.y };
  }
  return { kind: "territory", territory: info.object as TerritoryState, x: info.x, y: info.y };
}

/**
 * Region clicks have no territory-selection meaning (spec-112 C5 only
 * specifies hover for regions) — no-op rather than misinterpreting a
 * region feature as a `TerritoryState`.
 */
function handleMapClick(
  info: { object?: unknown },
  framing: AdminLevel,
  onTerritoryClick: ((territoryId: string) => void) | undefined,
): void {
  if (info.object && framing === "hex") {
    onTerritoryClick?.((info.object as TerritoryState).id);
  }
}

/**
 * Map `balkanization.sovereigns[]` (Sovereign -> Territory CLAIMS,
 * Constitution VIII.9) into `PolityClaim[]` for `layers/political.ts`'s
 * de-facto polity fills. `political.ts` needs county FIPS membership
 * (`memberFips`), but a Sovereign's real claims are over TERRITORY ids
 * (`claimed_territory_ids`, hex-native) — this resolves each claimed
 * territory to its real `county_fips` (a `TerritoryState` model field, not
 * derived) and de-dupes. A sovereign with no FIPS-resolvable claims (every
 * claimed territory missing from `territories`, or itself claiming
 * nothing) is omitted — an empty claim would draw a zero-county polity,
 * which `mergePolity` can't dissolve meaningfully. Claim color reuses the
 * SAME `factionStance`/`STANCE_COLOR` lookup the hex-native CLAIMS hulls
 * use (`buildClaimsHullLayers` above), so the political fill and the hex
 * ring/hull overlay never disagree about what color a sovereign's stance is.
 */
function buildPolityClaims(
  balkanization: BalkanizationBlock | null | undefined,
  territories: TerritoryState[],
): PolityClaim[] {
  if (!balkanization) return [];
  const fipsByTerritoryId = new Map(territories.map((t) => [t.id, t.county_fips]));
  const claims: PolityClaim[] = [];
  for (const sovereign of balkanization.sovereigns) {
    const memberFips = Array.from(
      new Set(
        sovereign.claimed_territory_ids
          .map((id) => fipsByTerritoryId.get(id))
          .filter((fips): fips is string => Boolean(fips)),
      ),
    );
    if (memberFips.length === 0) continue;
    const stance = factionStance(sovereign.ruling_faction_id, balkanization);
    const color: RGBAColor = stance ? STANCE_COLOR[stance] : [200, 168, 96, 200];
    claims.push({ polityId: sovereign.id, name: sovereign.id, color, memberFips });
  }
  return claims;
}

/**
 * Fetch both cartographic topologies (Lane Carto's `lib/geo/topology.ts`)
 * and commit each to its setter as it resolves — extracted to a top-level
 * function (spec-113 Lane B, cognitive-complexity budget) so `DeckGLMap`'s
 * mount effect is a one-line call. Returns the cleanup function React calls
 * on unmount; a load failure degrades honestly to "just absent" (no
 * fabricated placeholder, no crash) — `politicalLayers` is simply `[]`
 * until (unless) a topology resolves.
 */
function startTopologyLoad(
  setCountyTopology: (topo: CountyTopology) => void,
  setStateTopology: (topo: StateTopology) => void,
): () => void {
  let cancelled = false;
  loadCountyTopology()
    .then((topo) => {
      if (!cancelled) setCountyTopology(topo);
    })
    .catch(() => {
      // See docstring: honest absence, not a crash.
    });
  loadStateTopology()
    .then((topo) => {
      if (!cancelled) setStateTopology(topo);
    })
    .catch(() => {
      // See docstring: honest absence, not a crash.
    });
  return () => {
    cancelled = true;
  };
}

/**
 * Loads + composes the political cartography base layer stack (Lane Carto,
 * spec-113 §7) — de jure county hairlines + state borders, de facto polity
 * fills. Extracted to its own hook (spec-113 Lane B, cognitive-complexity
 * budget): owns the two topology fetches (mount-once, immutable substrate)
 * and their derived FeatureCollections/claims/layers, so `DeckGLMap`'s own
 * body only makes one call. Degrades honestly (`[]`, no fabricated
 * placeholder) until both topologies resolve.
 */
function usePoliticalLayers(
  balkanization: BalkanizationBlock | null | undefined,
  territories: TerritoryState[],
): ReturnType<typeof buildPoliticalLayers> {
  const [countyTopology, setCountyTopology] = useState<CountyTopology | null>(null);
  const [stateTopology, setStateTopology] = useState<StateTopology | null>(null);

  useEffect(() => startTopologyLoad(setCountyTopology, setStateTopology), []);

  const counties = useMemo(
    () => (countyTopology ? countyFeatures(countyTopology) : null),
    [countyTopology],
  );
  const states = useMemo(
    () => (stateTopology ? stateFeatures(stateTopology) : null),
    [stateTopology],
  );
  const polityClaims = useMemo(
    () => buildPolityClaims(balkanization, territories),
    [balkanization, territories],
  );
  return useMemo(
    () =>
      countyTopology && counties && states
        ? buildPoliticalLayers({
            topology: countyTopology,
            counties,
            states,
            claims: polityClaims,
            showContested: true,
          })
        : [],
    [countyTopology, counties, states, polityClaims],
  );
}

/**
 * Fixed per-lens ramp domain (DESIGN_BIBLE.md §3.2/§6: "no silent rescale
 * between ticks") + whether the CURRENT data would need a wider one (an
 * honest "flash" state, the same section's legend-flash requirement) —
 * extracted to its own hook (spec-113 Lane B, cognitive-complexity budget).
 *
 * Implemented as React's documented "adjust state during render" pattern
 * (https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes)
 * rather than a ref-backed cache (`lib/lenses/domainMemo.ts`'s
 * `createDomainMemo`, kept as a pure/unit-tested reference implementation
 * of the same rule but not wired in live here): reading/mutating a ref
 * during render is exactly the impurity `react-hooks/refs` exists to catch
 * (StrictMode double-render risk), and `setState` inside a `useEffect` body
 * trips `react-hooks/set-state-in-effect`. A plain, pure, conditional
 * `setState` call in the render body — keyed and idempotent — is React's
 * own blessed alternative for this exact "derive from previous renders"
 * shape. Hex framing never routes through this: its fill samples raw
 * territory values directly (`mapLensLayers.ts`'s `heatFill`/`metricFill`),
 * so a domain concept doesn't apply there.
 */
function useRampDomain(
  framing: AdminLevel,
  lens: Lens,
  regionFeatures: RegionFeature[],
): { fillDomain: FillDomain; legendFlash: boolean } {
  const [domainCache, setDomainCache] = useState<Record<string, FillDomain>>({});
  const naturalRegionDomain = useMemo(
    () =>
      computeFillDomain(
        lens,
        regionFeatures.map((f) => f.properties),
      ),
    [lens, regionFeatures],
  );
  const domainCacheKey = framing === "hex" ? null : lensKey(lens);
  const cachedDomain = domainCacheKey ? domainCache[domainCacheKey] : undefined;
  if (domainCacheKey && !cachedDomain) {
    setDomainCache((prev) => ({ ...prev, [domainCacheKey]: naturalRegionDomain }));
  }
  const fillDomain = cachedDomain ?? naturalRegionDomain;
  const legendFlash = Boolean(
    cachedDomain &&
    (naturalRegionDomain.min < cachedDomain.min || naturalRegionDomain.max > cachedDomain.max),
  );
  return { fillDomain, legendFlash };
}

/**
 * The three `layers` construction branches (region / hex / scatter
 * fallback), extracted to top-level functions (spec-113 Lane B) so
 * `DeckGLMap`'s own cognitive-complexity budget doesn't absorb their
 * branching — each owns its own budget instead. Pure given their params;
 * no hooks, no closures over component state.
 */
function buildRegionFramingLayers(params: {
  politicalLayers: ReturnType<typeof buildPoliticalLayers>;
  regionFeatures: RegionFeature[];
  lens: Lens;
  fillDomain: FillDomain;
  layerOpacity: number;
  rings: RingSpec[];
  hulls: HullSpec[];
  h3Territories: H3Territory[];
}) {
  const {
    politicalLayers,
    regionFeatures,
    lens,
    fillDomain,
    layerOpacity,
    rings,
    hulls,
    h3Territories,
  } = params;
  return [
    ...politicalLayers,
    buildRegionLayer(regionFeatures, lens, fillDomain, layerOpacity),
    ...buildRingLayers(rings, h3Territories),
    ...buildClaimsHullLayers(hulls, h3Territories),
  ];
}

function buildHexFramingLayers(params: {
  politicalLayers: ReturnType<typeof buildPoliticalLayers>;
  h3Territories: H3Territory[];
  getColor: (t: TerritoryState) => RGBAColor;
  layerOpacity: number;
  lens: Lens;
  factionFilter: string | null | undefined;
  rings: RingSpec[];
  hulls: HullSpec[];
}) {
  const {
    politicalLayers,
    h3Territories,
    getColor,
    layerOpacity,
    lens,
    factionFilter,
    rings,
    hulls,
  } = params;
  const baseHexLayer = new H3HexagonLayer<H3Territory>({
    id: "h3-hexagons",
    data: h3Territories,
    getHexagon: (t) => t.h3_index,
    getFillColor: getColor,
    getElevation: 0,
    extruded: false,
    opacity: layerOpacity,
    pickable: true,
    autoHighlight: true,
    highlightColor: [200, 168, 96, 180],
    updateTriggers: {
      getFillColor: [lens, factionFilter],
    },
  });
  return [
    ...politicalLayers,
    baseHexLayer,
    ...buildRingLayers(rings, h3Territories),
    ...buildClaimsHullLayers(hulls, h3Territories),
  ];
}

/** Territories without an `h3_index` — placed in a grid since no real coordinates exist. */
function buildScatterFallbackLayers(params: {
  politicalLayers: ReturnType<typeof buildPoliticalLayers>;
  territories: TerritoryState[];
  getColor: (t: TerritoryState) => RGBAColor;
  layerOpacity: number;
  lens: Lens;
  factionFilter: string | null | undefined;
}) {
  const { politicalLayers, territories, getColor, layerOpacity, lens, factionFilter } = params;
  const gridSize = Math.ceil(Math.sqrt(territories.length));
  return [
    ...politicalLayers,
    new ScatterplotLayer<TerritoryState & { _idx: number }>({
      id: "territory-dots",
      data: territories.map((t, i) => ({ ...t, _idx: i })),
      getPosition: (t: TerritoryState & { _idx: number }) => {
        const col = t._idx % gridSize;
        const row = Math.floor(t._idx / gridSize);
        return [
          INITIAL_VIEW_STATE.longitude - 10 + (col / gridSize) * 20,
          INITIAL_VIEW_STATE.latitude + 5 - (row / gridSize) * 10,
        ] as [number, number];
      },
      getFillColor: getColor,
      getRadius: 30000,
      radiusMinPixels: 12,
      radiusMaxPixels: 40,
      opacity: layerOpacity,
      pickable: true,
      autoHighlight: true,
      highlightColor: [200, 168, 96, 180],
      updateTriggers: {
        getFillColor: [lens, factionFilter],
      },
    }),
  ];
}

export function DeckGLMap({
  snapshot,
  mapData,
  lens,
  onLensChange,
  factionFilter = null,
  onFactionFilterChange,
  layerOpacity = DEFAULT_LAYER_OPACITY,
  onTerritoryClick,
  framing = "hex",
  onFramingChange,
}: DeckGLMapProps) {
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);

  const territories = snapshot.territories;
  const balkanization = mapData?.metadata?.balkanization ?? null;
  const availableMetrics = useMemo(() => availableMetricsFromMapData(mapData ?? null), [mapData]);

  // Political cartography base layer (Lane Carto, spec-113 §7) — de jure
  // county hairlines + state borders, de facto polity fills — see
  // `usePoliticalLayers`'s docstring.
  const politicalLayers = usePoliticalLayers(balkanization, territories);

  // Real aggregated features ship geometry: null, which the `geojson`
  // package's Feature type doesn't express — see RegionFeature's docstring.
  const regionFeatures = useMemo(
    () => (framing !== "hex" ? ((mapData?.features ?? []) as unknown as RegionFeature[]) : []),
    [mapData, framing],
  );

  // Ramp-domain memoization (DESIGN_BIBLE.md §3.2/§6: "no silent rescale
  // between ticks") — see `useRampDomain`'s docstring.
  const { fillDomain, legendFlash } = useRampDomain(framing, lens, regionFeatures);

  // -------------------------------------------------------------------
  // Hex framing branch — spec-113 Lane B: merge real per-hex metrics
  // (profit_rate/exploitation_rate/occ/imperial_rent/org_presence/
  // population/solidarity_index/dominant_class) from the hex-zoom `/map/`
  // response onto each territory, keyed by h3_index (hex features carry no
  // territory id of their own). Without this, metric/class_composition
  // lenses always rendered NO_DATA at hex framing — the only framing that
  // matters until mapSlice's default framing flips to "county" (Lane C).
  // -------------------------------------------------------------------
  const hexFeaturesByH3 = useMemo(
    () =>
      framing === "hex"
        ? hexFeaturePropertiesByH3(mapData ?? null)
        : new Map<string, HexMapFeatureProperties>(),
    [mapData, framing],
  );

  const hasH3 = useMemo(() => territories.some((t) => t.h3_index != null), [territories]);

  const lensResult = useMemo(
    () =>
      buildLensLayers({
        territories: territories.map((t) => territoryToLensTerritory(t, hexFeaturesByH3)),
        balkanization,
        lens,
        factionFilter,
      }),
    [territories, balkanization, lens, factionFilter, hexFeaturesByH3],
  );

  // Only show the legend-label chip for balkanization lenses when there's
  // real data — buildLensLayers always returns a usable (if "no data")
  // result, so we key off its legend text rather than a nullable result.
  const showLensLegendLabel =
    !BALKANIZATION_LENSES.has(lens.kind) ||
    !lensResult.legendLabel.toLowerCase().includes("no data");

  const getColor = useCallback(
    (t: TerritoryState): RGBAColor => lensResult.getFillColor(t.id),
    [lensResult],
  );

  // Legend marker (bible §3.2's Sylvester citation) — see currentValueForLens's docstring.
  const hexMarkerValues = useMemo(
    () => hexMarkerValuesForLens(lens, territories, hexFeaturesByH3),
    [lens, territories, hexFeaturesByH3],
  );
  const regionMarkerValues = useMemo(
    () => regionMarkerValuesForLens(lens, regionFeatures),
    [lens, regionFeatures],
  );
  const currentValue = useMemo(
    () => currentValueForLens(lens, framing, hexMarkerValues, regionMarkerValues, fillDomain),
    [lens, framing, hexMarkerValues, regionMarkerValues, fillDomain],
  );

  const layers = useMemo(() => {
    // h3Territories backs rings/hulls for BOTH the region and hex branches
    // below — those overlays are hex-native (spec-070 territory_influence/
    // sovereign CLAIMS) and framing-independent (see regionFillForLens's
    // faction/collapse docs: they remain the signal at every framing).
    const h3Territories = territories.filter((t): t is H3Territory => t.h3_index != null);

    if (framing !== "hex") {
      return buildRegionFramingLayers({
        politicalLayers,
        regionFeatures,
        lens,
        fillDomain,
        layerOpacity,
        rings: lensResult.rings,
        hulls: lensResult.hulls,
        h3Territories,
      });
    }

    if (hasH3) {
      return buildHexFramingLayers({
        politicalLayers,
        h3Territories,
        getColor,
        layerOpacity,
        lens,
        factionFilter,
        rings: lensResult.rings,
        hulls: lensResult.hulls,
      });
    }

    return buildScatterFallbackLayers({
      politicalLayers,
      territories,
      getColor,
      layerOpacity,
      lens,
      factionFilter,
    });
  }, [
    territories,
    hasH3,
    getColor,
    layerOpacity,
    lens,
    factionFilter,
    lensResult,
    framing,
    regionFeatures,
    fillDomain,
    politicalLayers,
  ]);

  return (
    <div className="relative flex h-full flex-col">
      <MapControls
        lens={lens}
        onLensChange={onLensChange}
        factionFilter={factionFilter}
        onFactionFilterChange={onFactionFilterChange}
        factions={balkanization?.factions}
        framing={framing}
        onFramingChange={onFramingChange}
        availability={{ balkanization, availableMetrics }}
        currentValue={currentValue}
        flash={legendFlash}
        legendStatusText={showLensLegendLabel ? lensResult.legendLabel : null}
      />

      {/* Map */}
      <div className="flex-1">
        <DeckGL
          initialViewState={INITIAL_VIEW_STATE}
          controller={true}
          layers={layers}
          onHover={(info) => setHoverInfo(resolveHoverInfo(info, framing))}
          onClick={(info) => handleMapClick(info, framing, onTerritoryClick)}
          style={{ position: "relative", width: "100%", height: "100%" }}
        >
          <MapLibreMap mapStyle={MAP_STYLE} />
        </DeckGL>
      </div>

      {/* Hover tooltip */}
      {hoverInfo?.kind === "territory" && (
        <HexTooltip territory={hoverInfo.territory} x={hoverInfo.x} y={hoverInfo.y} lens={lens} />
      )}
      {hoverInfo?.kind === "region" && (
        <RegionTooltip properties={hoverInfo.properties} x={hoverInfo.x} y={hoverInfo.y} />
      )}
    </div>
  );
}
