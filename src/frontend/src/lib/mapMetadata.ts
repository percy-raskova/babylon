/**
 * `panels.map`'s `Panel<FeatureCollection>` typing doesn't carry the
 * backend's extra `metadata` key (`EngineBridge.get_map_snapshot` attaches
 * it outside the GeoJSON spec) — this is the one cast site so every
 * consumer (MapPanel, Outliner's faction list) reads the balkanization
 * block the same way `DeckGLMap` already does.
 */

import type { FeatureCollection } from "geojson";
import type { MapSnapshotMetadata } from "@/types/game";
import type { FactionSummary } from "@/components/map/mapLensLayers";

export type MapFeatureCollectionWithMetadata = FeatureCollection & {
  metadata?: MapSnapshotMetadata;
};

/** Read the spec-070 faction list off a fetched map panel's data, or `[]` when absent. */
export function factionsFromMapData(data: FeatureCollection | null): FactionSummary[] {
  const withMeta = data as MapFeatureCollectionWithMetadata | null;
  return withMeta?.metadata?.balkanization?.factions ?? [];
}

/** Read `metadata.available_metrics` off a fetched map panel's data, or `undefined` when absent. */
export function availableMetricsFromMapData(data: FeatureCollection | null): string[] | undefined {
  const withMeta = data as MapFeatureCollectionWithMetadata | null;
  return withMeta?.metadata?.available_metrics;
}

/**
 * One hex-zoom (`?zoom=hex`) `/map/` feature's `properties` bag
 * (`_hex_feature_properties`, `web/game/engine_bridge.py`) — the raw values
 * `DeckGLMap` merges onto each `LensTerritory` (spec-113 Lane B) so
 * metric/class_composition lenses have real data to fill hex framing with,
 * not just the aggregated-region framing `regionFillForLens` already
 * covered. All fields optional/nullable: an older/stubbed fixture may not
 * carry every key, and the real backend emits explicit `null` for coverage
 * gaps (Constitution III.11 — never fabricated here either).
 */
export interface HexMapFeatureProperties {
  h3_index: string;
  profit_rate?: number | null;
  exploitation_rate?: number | null;
  occ?: number | null;
  imperial_rent?: number | null;
  heat?: number | null;
  org_presence?: number | null;
  population?: number | null;
  habitability?: number | null;
  dominant_class?: string | null;
  solidarity_index?: number | null;
  /**
   * Wave 2 Round 2 (`reports/wave2-implementation-map.md`, ruling 1):
   * Pi = τ_through / τ_national, wired for real this round — no longer the
   * frozen `1.0` constant. Null/absent is honest no-data.
   */
  throughput_position?: number | null;
  /**
   * Wave 2 Round 2: `_agitation_index_by_territory`'s pop-weighted mean of
   * `SocialClass.ideology.agitation`. DECLARED_CONDITIONAL — legitimately
   * `0.0` at tick 0 / absent a falling-wage/rent/Φ/g₃₃ crisis tick, never
   * fabricated warmth.
   */
  agitation?: number | null;
  /**
   * Wave 2 Round 2: the real `TerritoryType` enum's `.value`
   * (`src/babylon/models/enums/territory.py`: core/periphery/reservation/
   * penal_colony/concentration_camp) — NOT `stub_bridge.py`'s legacy
   * `"URBAN"/"SUBURBAN"/"PERIURBAN"` vocabulary. Categorical.
   */
  territory_type?: string | null;
  [key: string]: unknown;
}

/**
 * Index a hex-zoom `/map/` FeatureCollection's features by `properties.h3_index`
 * (the join key `DeckGLMap` uses against each `TerritoryState.h3_index` — hex
 * features carry no territory id, only their own `h3_index`). Returns an
 * empty map for `null`/non-hex/malformed data — callers should only invoke
 * this when `framing === "hex"` (aggregated-region features carry
 * `member_h3` instead, a different join shape entirely).
 */
export function hexFeaturePropertiesByH3(
  data: FeatureCollection | null,
): Map<string, HexMapFeatureProperties> {
  const index = new Map<string, HexMapFeatureProperties>();
  const withMeta = data as MapFeatureCollectionWithMetadata | null;
  for (const feature of withMeta?.features ?? []) {
    const props = feature.properties as HexMapFeatureProperties | null | undefined;
    if (props?.h3_index) {
      index.set(props.h3_index, props);
    }
  }
  return index;
}
