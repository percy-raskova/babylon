/**
 * deck.gl + MapLibre hex map visualization.
 *
 * Renders territories as H3 hexagons (when h3_index is available)
 * or as ScatterplotLayer dots (fallback). Color encodes the active `Lens`.
 *
 * Adapted (spec-110 B2) to the unified `Lens` discriminated union
 * (`@/lib/lens`) and decoupled from both `mapStore` (stores are B3
 * territory) and `react-router` (routing is B3 territory): this is now a
 * controlled component — the active lens, faction filter, and territory
 * click all come in via props/callbacks instead of zustand state and
 * `useNavigate`. There is exactly one fill axis now (`lens`), not the old
 * `activeLayer` + `lensMode` pair — `buildLensLayers` always returns a
 * usable `getFillColor`, including a graceful "no data" fill for
 * balkanization-derived lenses when that block is absent, so no separate
 * metric-ramp fallback path is needed.
 */

import { useCallback, useMemo, useState } from "react";
import { DeckGL } from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import type { RGBAColor } from "@/theme/colors";

import { MapLegend } from "@/components/map/MapLegend";
import { HexTooltip } from "@/components/map/HexTooltip";
import { MapModeSelector } from "@/components/map/MapModeSelector";
import {
  BALKANIZATION_LENSES,
  buildLensLayers,
  type RingSpec,
  type HullSpec,
} from "@/components/map/mapLensLayers";
import { hullPolygonForTerritories } from "@/components/map/mapLensGeometry";
import type { Lens } from "@/lib/lens";
import type { GameSnapshot, TerritoryState, MapSnapshotMetadata } from "@/types/game";
import type { FeatureCollection } from "geojson";

type H3Territory = TerritoryState & { h3_index: string };

/** Default fill opacity when the caller doesn't specify one. */
const DEFAULT_LAYER_OPACITY = 0.8;

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

/** Dark basemap style with actual map tiles (Carto Dark Matter). */
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

/** Default view centered on Southeast Michigan. */
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
}: DeckGLMapProps) {
  const [hoverInfo, setHoverInfo] = useState<{
    territory: TerritoryState;
    x: number;
    y: number;
  } | null>(null);

  const territories = snapshot.territories;
  const balkanization = mapData?.metadata?.balkanization ?? null;

  const hasH3 = useMemo(() => territories.some((t) => t.h3_index != null), [territories]);

  const lensResult = useMemo(
    () =>
      buildLensLayers({
        territories: territories.map((t) => ({
          id: t.id,
          h3_index: t.h3_index,
          heat: t.heat,
          biocapacity: t.biocapacity,
          // Spec-109 A2: real Territory field, was hardcoded to 100.
          max_biocapacity: t.max_biocapacity ?? 100,
          habitability: t.habitability ?? null,
        })),
        balkanization,
        lens,
        factionFilter,
      }),
    [territories, balkanization, lens, factionFilter],
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

  const layers = useMemo(() => {
    if (hasH3) {
      const h3Territories = territories.filter(
        (t): t is TerritoryState & { h3_index: string } => t.h3_index != null,
      );
      const baseHexLayer = new H3HexagonLayer<TerritoryState & { h3_index: string }>({
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
        baseHexLayer,
        ...buildRingLayers(lensResult.rings, h3Territories),
        ...buildClaimsHullLayers(lensResult.hulls, h3Territories),
      ];
    }

    // Fallback: ScatterplotLayer for territories without h3_index
    // Place them in a grid pattern since we don't have real coordinates
    const gridSize = Math.ceil(Math.sqrt(territories.length));
    return [
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
  }, [territories, hasH3, getColor, layerOpacity, lens, factionFilter, lensResult]);

  return (
    <div className="relative flex h-full flex-col">
      {/* Controls */}
      <div className="absolute left-3 top-3 z-10 flex flex-col gap-2 rounded-md bg-void/80 p-2 backdrop-blur-sm">
        <MapLegend lens={lens} />
        {showLensLegendLabel && (
          <span
            data-testid="lens-legend-label"
            className="text-[10px] uppercase tracking-wider text-ash"
          >
            {lensResult.legendLabel}
          </span>
        )}
      </div>

      {/* Political-topology lens mode selector */}
      <div className="absolute right-3 top-3 z-10">
        <MapModeSelector
          lens={lens}
          onLensChange={onLensChange}
          factionFilter={factionFilter}
          onFactionFilterChange={onFactionFilterChange}
          factions={balkanization?.factions}
        />
      </div>

      {/* Map */}
      <div className="flex-1">
        <DeckGL
          initialViewState={INITIAL_VIEW_STATE}
          controller={true}
          layers={layers}
          onHover={(info) => {
            if (info.object) {
              setHoverInfo({
                territory: info.object as TerritoryState,
                x: info.x,
                y: info.y,
              });
            } else {
              setHoverInfo(null);
            }
          }}
          onClick={(info) => {
            if (info.object) {
              const territoryId = (info.object as TerritoryState).id;
              onTerritoryClick?.(territoryId);
            }
          }}
          style={{ position: "relative", width: "100%", height: "100%" }}
        >
          <Map mapStyle={MAP_STYLE} />
        </DeckGL>
      </div>

      {/* Hover tooltip */}
      {hoverInfo && (
        <HexTooltip territory={hoverInfo.territory} x={hoverInfo.x} y={hoverInfo.y} lens={lens} />
      )}
    </div>
  );
}
