/**
 * MapPanel preview — the persistent center map region. Store-driven:
 * shows the honest "No world state loaded yet." empty before any world
 * snapshot, and mounts `DeckGLMap` (deck.gl + MapLibre) once one is
 * seeded. Per the lane brief, this preview does not fight WebGL — in
 * headless capture the hex/basemap canvas may render blank (no GPU
 * compositor and/or no network access for the external basemap tiles);
 * the chrome around it (MapLegend, MapModeSelector, the lens legend
 * label) is plain HTML/CSS and is the actual thing under review here.
 *
 * Two gotchas worked around here (both written up in
 * .design-sync/learnings/shell.md):
 *  1. Sizing is an inline `style` (`display:"grid"` + explicit
 *     width/height), not Tailwind arbitrary classes — Tailwind's content
 *     scan never walks `.design-sync/previews/`, so a unique `h-[520px]`
 *     or `[&>main]:h-full` class there compiles to nothing, and the bare
 *     `<main>` (no intrinsic height outside the real AppShell grid)
 *     collapses to ~0px, which in turn collapses `DeckGLMap`'s `h-full`
 *     wrapper — the whole map area (including the plain-HTML chrome)
 *     disappears, not just the WebGL canvas. `display:grid` on the
 *     wrapper makes its sole child (`<main>`) stretch to fill the cell
 *     by CSS Grid's own default, with no need to target the child's tag.
 *  2. `map.fetch` is overridden to a no-op — `MapPanel`'s mount effect
 *     always fires `fetchMap(gameId)` against the capture harness's
 *     static file server (a real HTTP 404); harmless here since neither
 *     `MapPanel` nor `DeckGLMap` reads `panels.map.error`, but a no-op
 *     keeps every cell deterministic and avoids a pointless failed fetch.
 *
 * Card shows the primary story only (needs cfg.overrides.MapPanel =
 * {cardMode:"single", primaryStory:"Populated"}).
 */
import { MapPanel, useStore } from "babylon-cockpit";

const TERRITORIES = [
  {
    id: "territory-detroit-mi",
    name: "Detroit",
    h3_index: "882a100d2bfffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.55,
    sector_type: "urban_core",
    territory_type: "metropolitan",
    profile: "HIGH_PROFILE",
    rent_level: 0.62,
    population: 639111,
    under_eviction: true,
    biocapacity: 0.28,
    max_biocapacity: 100,
    habitability: 0.31,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-dearborn-mi",
    name: "Dearborn",
    h3_index: "882a100d2cfffff",
    h3_resolution: 7,
    county_fips: "26163",
    heat: 0.22,
    sector_type: "residential",
    territory_type: "metropolitan",
    profile: "LOW_PROFILE",
    rent_level: 0.4,
    population: 109976,
    under_eviction: false,
    biocapacity: 0.4,
    max_biocapacity: 100,
    habitability: null,
    host_id: null,
    occupant_id: null,
  },
];

const BALKANIZATION = {
  factions: [
    { id: "FAC_DECOLONIAL", colonial_stance: "abolish", is_settler_formation: false },
    { id: "FAC_LOYALIST", colonial_stance: "uphold", is_settler_formation: true },
  ],
  sovereigns: [],
  territory_influence: [],
};

function seedPopulatedMap(lens: Record<string, unknown>, factionFilter: string | null) {
  useStore.setState((s: any) => ({
    world: {
      ...s.world,
      snapshot: { tick: 104, territories: TERRITORIES, organizations: [], events: [] },
    },
    panels: {
      ...s.panels,
      map: {
        ...s.panels.map,
        data: { type: "FeatureCollection", features: [], metadata: { balkanization: BALKANIZATION } },
        loading: false,
        error: null,
        fetch: async () => {},
      },
    },
    map: { ...s.map, lens, framing: "county", factionFilter, selection: null },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return (
    <div style={{ display: "grid", width: 880, height: 520 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

export function EmptyNoWorldState() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: null },
    panels: {
      ...s.panels,
      map: { ...s.panels.map, data: null, loading: false, error: null, fetch: async () => {} },
    },
  }));
  return (
    <Frame>
      <MapPanel gameId="wayne-county-001" />
    </Frame>
  );
}

export function Populated() {
  seedPopulatedMap({ kind: "stance" }, null);
  return (
    <Frame>
      <MapPanel gameId="wayne-county-001" />
    </Frame>
  );
}

export function FactionLens() {
  seedPopulatedMap({ kind: "faction" }, "FAC_DECOLONIAL");
  return (
    <Frame>
      <MapPanel gameId="wayne-county-001" />
    </Frame>
  );
}
