import { useState, useMemo, useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import type { FeatureCollection, Feature, Geometry } from "geojson";
import { metricToColor } from "../utils/colorScale";
import "leaflet/dist/leaflet.css";

// Fix Leaflet CSS issues in React using generic L
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface HexMapProps {
  /** The new GeoJSON data to render (Step 7/8/9) */
  data?: FeatureCollection | null;
  /** Active metric, e.g. 'heat', 'profit_rate'. If omitted, uses local state. */
  activeMetric?: string;
  minVal?: number;
  maxVal?: number;
  onSelectNode?: (nodeId: string) => void;
}

const AVAILABLE_METRICS = [
  "heat",
  "profit_rate",
  "exploitation_rate",
  "occ",
  "imperial_rent",
  "org_presence",
] as const;

function MapBounds({ data }: { data?: FeatureCollection | null }) {
  const map = useMap();
  useEffect(() => {
    // Zoom to metadata bounds if provided by the backend GeoJSON envelope
    const b = (
      data as FeatureCollection & {
        metadata?: { bounds?: { sw: [number, number]; ne: [number, number] } };
      }
    )?.metadata?.bounds;
    if (b && Array.isArray(b.sw) && Array.isArray(b.ne)) {
      map.fitBounds(
        [
          [b.sw[0], b.sw[1]],
          [b.ne[0], b.ne[1]],
        ],
        { padding: [20, 20] },
      );
    }
  }, [data, map]);
  return null;
}

export function HexMap({
  data,
  activeMetric: initialMetric = "heat",
  minVal = 0,
  maxVal = 100,
  onSelectNode,
}: HexMapProps) {
  const [metric, setMetric] = useState<string>(initialMetric);

  // Center roughly over North America
  const center: [number, number] = [39.8283, -98.5795];

  // Dynamically calculate actual min/max for the current metric viewport
  const { computedMin, computedMax } = useMemo(() => {
    if (!data?.features || data.features.length === 0) {
      return { computedMin: minVal, computedMax: maxVal };
    }
    let min = Infinity;
    let max = -Infinity;
    data.features.forEach((f) => {
      const val = f.properties?.[metric];
      if (typeof val === "number") {
        if (val < min) min = val;
        if (val > max) max = val;
      }
    });

    if (min === Infinity || max === -Infinity) {
      return { computedMin: minVal, computedMax: maxVal };
    }

    // Fallback if data is entirely uniform
    if (min === max) {
      return { computedMin: min - 1, computedMax: max + 1 };
    }

    return { computedMin: min, computedMax: max };
  }, [data, metric, minVal, maxVal]);

  const styleFeature = (feature?: Feature<Geometry, Record<string, unknown>>) => {
    if (!feature) return { fillColor: "#808080", weight: 1, fillOpacity: 0.8, color: "#1a1a2a" };

    const value = feature.properties?.[metric];
    if (typeof value !== "number") {
      return { fillColor: "#808080", weight: 1, fillOpacity: 0.8, color: "#1a1a2a" };
    }

    const color = metricToColor(value, computedMin, computedMax, metric);
    return {
      fillColor: color,
      fillOpacity: 0.7, // Allow the dark basemap to show through slightly
      weight: 1,
      color: "#1a1a2a", // --color-soot / hex boundaries
    };
  };

  // GeoJSON key to force re-render when data or metric changes
  const geoJsonKey = data ? `${metric}-${data.features?.length || 0}` : `empty-${metric}`;

  return (
    <div className="relative flex h-full w-full flex-col bg-void">
      {/* Metric Selector Controls */}
      <div className="absolute top-2 left-2 z-[1000] flex flex-col gap-1 rounded bg-void/80 p-2 border border-soot backdrop-blur-sm shadow-xl">
        <span className="text-xs uppercase tracking-wider text-ash mb-1">Color map by:</span>
        {AVAILABLE_METRICS.map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`rounded border px-2 py-1 text-left text-[11px] font-mono transition-colors ${
              metric === m
                ? "border-gold bg-[#1a1a30] text-gold"
                : "border-wet-concrete bg-transparent text-ash hover:border-silver"
            }`}
          >
            {m}
          </button>
        ))}
        {/* Debug Info Overlay */}
        <div className="mt-2 text-[9px] font-mono text-ash/60">
          <div>
            Range: {computedMin.toFixed(3)} - {computedMax.toFixed(3)}
          </div>
        </div>
      </div>

      <div className="flex-1 w-full h-full relative z-0">
        <MapContainer
          center={center}
          zoom={4}
          style={{ height: "100%", width: "100%", backgroundColor: "var(--color-void)" }}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
          />
          <MapBounds data={data} />
          {data && (
            <GeoJSON
              key={geoJsonKey}
              data={data}
              style={styleFeature}
              onEachFeature={(feature, layer) => {
                layer.on({
                  click: () => {
                    if (onSelectNode && feature.properties?.id) {
                      onSelectNode(feature.properties.id as string);
                    }
                  },
                });
              }}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
