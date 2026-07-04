/**
 * deck.gl + MapLibre hex map visualization.
 *
 * Renders territories as H3 hexagons (when h3_index is available)
 * or as ScatterplotLayer dots (fallback). Color encodes the active map layer.
 */

import { useCallback, useMemo, useState } from "react";
import { DeckGL } from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useMapStore } from "@/stores/mapStore";
import { getColorScale, type RGBAColor } from "@/theme/colors";

import { MapLegend } from "@/components/map/MapLegend";
import { HexTooltip } from "@/components/map/HexTooltip";
import { FramingSelector } from "@/components/map/FramingSelector";
import { MapModeSelector } from "@/components/map/MapModeSelector";
import { buildLensLayers, type RingSpec, type HullSpec } from "@/components/map/mapLensLayers";
import { hullPolygonForTerritories } from "@/components/map/mapLensGeometry";
import { useNavigate, useParams } from "react-router";
import type { GameSnapshot, TerritoryState, MapLayer } from "@/types/game";

type H3Territory = TerritoryState & { h3_index: string };

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

/** Extract metric value from territory for color encoding. */
function getMetricValue(territory: TerritoryState, layer: MapLayer): number {
  switch (layer) {
    case "heat":
      return territory.heat;
    case "consciousness":
      return 0;
    case "wealth":
      return territory.rent_level;
    case "rent":
      return territory.rent_level;
    case "biocapacity":
      return territory.biocapacity;
    case "population":
      return Math.min(territory.population / 1_000_000, 1);
    case "profit_rate":
    case "exploitation_rate":
    case "occ":
    case "imperial_rent":
    case "org_presence":
      // Extended metrics — render with rent_level as fallback
      return territory.rent_level;
  }
}

interface DeckGLMapProps {
  snapshot: GameSnapshot;
}

export function DeckGLMap({ snapshot }: DeckGLMapProps) {
  const activeLayer = useMapStore((s) => s.activeLayer);
  const layerOpacity = useMapStore((s) => s.layerOpacity);
  const lensMode = useMapStore((s) => s.lensMode);
  const factionFilter = useMapStore((s) => s.factionFilter);
  const navigate = useNavigate();
  const { id: gameId = "" } = useParams<{ id: string }>();
  const [hoverInfo, setHoverInfo] = useState<{
    territory: TerritoryState;
    x: number;
    y: number;
  } | null>(null);

  const territories = snapshot.territories;
  const balkanization = snapshot.balkanization ?? null;
  const colorScale = useMemo(() => getColorScale(activeLayer), [activeLayer]);

  const hasH3 = useMemo(() => territories.some((t) => t.h3_index != null), [territories]);

  // Spec-093 US3: political-topology lens (stance/heat/habitability/faction/
  // collapse) over spec-070 balkanization data. Distinct axis from
  // `activeLayer`'s single-metric ramp. Degrades to `null` (no lens layer,
  // falls back to `activeLayer`'s existing fill) when the session has no
  // balkanization data yet — see `mapLensLayers.ts`'s module docstring.
  const lensResult = useMemo(() => {
    if (!balkanization) return null;
    return buildLensLayers({
      territories: territories.map((t) => ({
        id: t.id,
        h3_index: t.h3_index,
        heat: t.heat,
        biocapacity: t.biocapacity,
        max_biocapacity: 100,
      })),
      balkanization,
      lensMode,
      factionFilter,
    });
  }, [territories, balkanization, lensMode, factionFilter]);

  const getColor = useCallback(
    (t: TerritoryState): RGBAColor => {
      if (lensResult) return lensResult.getFillColor(t.id);
      const v = Math.max(0, Math.min(1, getMetricValue(t, activeLayer)));
      return colorScale(v);
    },
    [activeLayer, colorScale, lensResult],
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
          getFillColor: [activeLayer, lensMode, factionFilter],
        },
      });
      if (!lensResult) return [baseHexLayer];
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
          getFillColor: [activeLayer, lensMode, factionFilter],
        },
      }),
    ];
  }, [
    territories,
    hasH3,
    getColor,
    layerOpacity,
    activeLayer,
    lensMode,
    factionFilter,
    lensResult,
  ]);

  return (
    <div className="relative flex h-full flex-col">
      {/* Controls */}
      <div className="absolute left-3 top-3 z-10 flex flex-col gap-2 rounded-md bg-void/80 p-2 backdrop-blur-sm">
        <MapLegend />
        {lensResult && (
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
        <MapModeSelector />
      </div>

      {/* Framing level selector */}
      <div className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2">
        <FramingSelector />
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
              navigate(`/games/${gameId}/intel/territory/${territoryId}`);
            }
          }}
          style={{ position: "relative", width: "100%", height: "100%" }}
        >
          <Map mapStyle={MAP_STYLE} />
        </DeckGL>
      </div>

      {/* Hover tooltip */}
      {hoverInfo && <HexTooltip territory={hoverInfo.territory} x={hoverInfo.x} y={hoverInfo.y} />}
    </div>
  );
}
