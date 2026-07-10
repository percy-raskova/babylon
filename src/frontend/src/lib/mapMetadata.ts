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
