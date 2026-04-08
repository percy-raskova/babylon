import { useState } from "react";
import { HexMap } from "./components/HexMap";
import type { FeatureCollection } from "geojson";

// We import the static fixture data to directly verify rendering
// without needing the live backend API.
import mockMapData from "./fixtures/mock_map_data.json";

export function DevHarness() {
  const [data] = useState<FeatureCollection | null>(mockMapData as FeatureCollection);

  return (
    <div className="flex h-screen w-screen flex-col bg-void text-bone">
      {/* Harness Header */}
      <div className="shrink-0 border-b border-soot bg-dark-metal px-6 py-4">
        <h1 className="text-xl font-bold text-gold tracking-widest">HEXMAP DEV HARNESS</h1>
        <p className="text-sm text-ash mt-1">Standalone component testing environment.</p>
      </div>

      {/* Main Map Area */}
      <div className="flex-1 relative">
        <HexMap
          data={data}
          activeMetric="profit_rate"
          minVal={0}
          maxVal={0.5}
          onSelectNode={(id) => console.log(`Selected node: ${id}`)}
        />
      </div>
    </div>
  );
}
