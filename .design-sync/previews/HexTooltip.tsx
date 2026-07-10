/**
 * HexTooltip preview — the floating hover card for a hex/territory,
 * metrics reordered by the active map Lens. Pure props (territory, x, y,
 * lens), no store. Positioned absolute internally, so each cell needs a
 * `position: relative` frame to anchor into.
 */
import { HexTooltip } from "babylon-cockpit";

function territory(overrides: Record<string, unknown> = {}) {
  return {
    id: "territory-detroit-downtown",
    name: "Detroit Downtown",
    h3_index: "862ab2c5fffffff",
    h3_resolution: 6,
    county_fips: "26163",
    heat: 0.71,
    sector_type: "urban_core",
    territory_type: "metropolitan",
    profile: "HIGH_PROFILE",
    rent_level: 0.62,
    population: 84213,
    under_eviction: false,
    biocapacity: 0.18,
    max_biocapacity: 100,
    habitability: 0.24,
    host_id: null,
    occupant_id: "org-uaw-local-600",
    ...overrides,
  };
}

// Inline style for the pixel box: .design-sync/previews/ isn't in
// Tailwind's content-scan root, so w-[Npx]/h-[Npx] classes never compile
// (see learnings). Harmless here (the tooltip is absolutely positioned and
// renders fine regardless), but kept consistent with the other frames.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="relative bg-void p-2" style={{ width: 400, height: 220 }}>
      {children as never}
    </div>
  );
}

export function HeatLensPriority() {
  return (
    <Frame>
      <HexTooltip territory={territory()} x={30} y={30} lens={{ kind: "heat" }} />
    </Frame>
  );
}

export function PopulationMetricPriority() {
  return (
    <Frame>
      <HexTooltip territory={territory()} x={30} y={30} lens={{ kind: "metric", metric: "population" }} />
    </Frame>
  );
}

export function UnderEvictionWarning() {
  return (
    <Frame>
      <HexTooltip
        territory={territory({
          id: "territory-dearborn",
          name: "Dearborn",
          under_eviction: true,
          rent_level: 0.81,
          profile: "HIGH_PROFILE",
        })}
        x={30}
        y={30}
        lens={{ kind: "stance" }}
      />
    </Frame>
  );
}

export function HabitabilityNullHonesty() {
  return (
    <Frame>
      <HexTooltip
        territory={territory({
          id: "territory-pontiac",
          name: "Pontiac",
          habitability: null,
          biocapacity: 0.27,
        })}
        x={30}
        y={30}
        lens={{ kind: "habitability" }}
      />
    </Frame>
  );
}
