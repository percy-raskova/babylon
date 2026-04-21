/**
 * deck.gl + MapLibre hex map visualization.
 *
 * Renders territories as H3 hexagons (when h3_index is available)
 * or as ScatterplotLayer dots (fallback). Color encodes the active map layer.
 */

import { useCallback, useMemo, useState } from "react";
import { DeckGL } from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useMapStore } from "@/stores/mapStore";
import { useUIStore } from "@/stores/uiStore";
import { getColorScale, type RGBAColor } from "@/theme/colors";
import { LayerControls } from "@/components/map/LayerControls";
import { MapLegend } from "@/components/map/MapLegend";
import { HexTooltip } from "@/components/map/HexTooltip";
import { FramingSelector } from "@/components/map/FramingSelector";
import type { GameSnapshot, TerritoryState, MapLayer } from "@/types/game";

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
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const [hoverInfo, setHoverInfo] = useState<{
    territory: TerritoryState;
    x: number;
    y: number;
  } | null>(null);

  const territories = snapshot.territories;
  const colorScale = useMemo(() => getColorScale(activeLayer), [activeLayer]);

  const hasH3 = useMemo(() => territories.some((t) => t.h3_index != null), [territories]);

  const getColor = useCallback(
    (t: TerritoryState): RGBAColor => {
      const v = Math.max(0, Math.min(1, getMetricValue(t, activeLayer)));
      return colorScale(v);
    },
    [activeLayer, colorScale],
  );

  const layers = useMemo(() => {
    if (hasH3) {
      const h3Territories = territories.filter(
        (t): t is TerritoryState & { h3_index: string } => t.h3_index != null,
      );
      return [
        new H3HexagonLayer<TerritoryState & { h3_index: string }>({
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
            getFillColor: [activeLayer],
          },
        }),
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
          getFillColor: [activeLayer],
        },
      }),
    ];
  }, [territories, hasH3, getColor, layerOpacity, activeLayer]);

  return (
    <div className="relative flex h-full flex-col">
      {/* Controls */}
      <div className="absolute left-3 top-3 z-10 flex flex-col gap-2 rounded-md bg-void/80 p-2 backdrop-blur-sm">
        <LayerControls />
        <MapLegend />
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
              setSelectedHex((info.object as TerritoryState).id);
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
