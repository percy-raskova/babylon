/**
 * DeckGLMap preview — deck.gl + MapLibre hex map over Southeast Michigan.
 * Prop-only controlled component (no store reads), so every cell just
 * passes a different snapshot/mapData/lens.
 *
 * Territories carry REAL res-6 H3 cells (computed via h3-js's
 * `latLngToCell` for actual Detroit-metro coordinates — Downtown, Dearborn,
 * Warren, Southfield, Pontiac, Redford) so the hex layer has genuine
 * geometry to paint. WebGL in headless chromium is a known risk for this
 * component (see learnings) — this is the one honest attempt.
 */
import { DeckGLMap } from "babylon-cockpit";

const WAYNE_TERRITORIES = [
  {
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
    under_eviction: true,
    biocapacity: 0.18,
    max_biocapacity: 100,
    habitability: 0.24,
    host_id: null,
    occupant_id: "org-uaw-local-600",
  },
  {
    id: "territory-dearborn",
    name: "Dearborn",
    h3_index: "862ab2cc7ffffff",
    h3_resolution: 6,
    county_fips: "26163",
    heat: 0.54,
    sector_type: "industrial",
    territory_type: "metropolitan",
    profile: "HIGH_PROFILE",
    rent_level: 0.48,
    population: 39247,
    under_eviction: false,
    biocapacity: 0.29,
    max_biocapacity: 100,
    habitability: 0.41,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-warren",
    name: "Warren",
    h3_index: "862ab2d57ffffff",
    h3_resolution: 6,
    county_fips: "26163",
    heat: 0.38,
    sector_type: "industrial",
    territory_type: "suburban",
    profile: "MEDIUM_PROFILE",
    rent_level: 0.4,
    population: 68812,
    under_eviction: false,
    biocapacity: 0.35,
    max_biocapacity: 100,
    habitability: 0.52,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-southfield",
    name: "Southfield",
    h3_index: "862ab2c17ffffff",
    h3_resolution: 6,
    county_fips: "26125",
    heat: 0.22,
    sector_type: "commercial",
    territory_type: "suburban",
    profile: "LOW_PROFILE",
    rent_level: 0.55,
    population: 32456,
    under_eviction: false,
    biocapacity: 0.44,
    max_biocapacity: 100,
    habitability: 0.63,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-pontiac",
    name: "Pontiac",
    h3_index: "862ab2db7ffffff",
    h3_resolution: 6,
    county_fips: "26125",
    heat: 0.46,
    sector_type: "industrial",
    territory_type: "suburban",
    profile: "MEDIUM_PROFILE",
    rent_level: 0.37,
    population: 21201,
    under_eviction: false,
    biocapacity: 0.27,
    max_biocapacity: 100,
    habitability: 0.34,
    host_id: null,
    occupant_id: null,
  },
  {
    id: "territory-redford",
    name: "Redford",
    h3_index: "862ab2c8fffffff",
    h3_resolution: 6,
    county_fips: "26163",
    heat: 0.31,
    sector_type: "residential",
    territory_type: "suburban",
    profile: "LOW_PROFILE",
    rent_level: 0.33,
    population: 48250,
    under_eviction: false,
    biocapacity: 0.4,
    max_biocapacity: 100,
    habitability: 0.58,
    host_id: null,
    occupant_id: null,
  },
];

function makeSnapshot() {
  return {
    tick: 104,
    session_id: "wayne-county-104",
    territories: WAYNE_TERRITORIES,
  };
}

const BALKANIZATION = {
  factions: [
    { id: "FAC_COMPRADOR_BLOC", colonial_stance: "uphold" },
    { id: "FAC_NEW_AFRIKAN_UNITY", colonial_stance: "abolish", is_settler_formation: false },
    { id: "FAC_LIBERAL_TECHNOCRAT", colonial_stance: "ignore" },
  ],
  sovereigns: [
    {
      id: "SOV_DETROIT_METRO",
      ruling_faction_id: "FAC_COMPRADOR_BLOC",
      extraction_policy: "tribute_maximizing",
      legitimacy: 0.38,
      claimed_territory_ids: [
        "territory-detroit-downtown",
        "territory-dearborn",
        "territory-warren",
      ],
    },
  ],
  territory_influence: [
    {
      territory_id: "territory-detroit-downtown",
      influences: [
        { faction_id: "FAC_NEW_AFRIKAN_UNITY", influence_level: 0.58, support_type: "material" },
        { faction_id: "FAC_COMPRADOR_BLOC", influence_level: 0.42, support_type: "coercive" },
      ],
      dominant_faction_id: "FAC_NEW_AFRIKAN_UNITY",
      current_sovereign_id: "SOV_DETROIT_METRO",
      contested: true,
      habitability: 0.24,
    },
    {
      territory_id: "territory-dearborn",
      influences: [
        { faction_id: "FAC_COMPRADOR_BLOC", influence_level: 0.66, support_type: "coercive" },
      ],
      dominant_faction_id: "FAC_COMPRADOR_BLOC",
      current_sovereign_id: "SOV_DETROIT_METRO",
      contested: false,
      habitability: 0.41,
    },
    {
      territory_id: "territory-warren",
      influences: [
        { faction_id: "FAC_LIBERAL_TECHNOCRAT", influence_level: 0.51, support_type: "material" },
      ],
      dominant_faction_id: "FAC_LIBERAL_TECHNOCRAT",
      current_sovereign_id: null,
      contested: false,
      habitability: 0.52,
    },
  ],
};

function mapDataWith(balkanization: unknown) {
  return {
    type: "FeatureCollection" as const,
    features: [],
    metadata: { balkanization },
  };
}

// Tailwind arbitrary-value classes (w-[Npx]/h-[Npx]) never compile here —
// .design-sync/previews/ sits outside the app's Tailwind content-scan root
// (buildCmd runs `vite build` from src/frontend/), so those classes have
// zero generated CSS and the div collapses to auto height. DeckGLMap's
// root is `h-full`, which needs a REAL ancestor pixel height to resolve —
// inline style bypasses Tailwind generation entirely and is not subject to
// that gap (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void" style={{ width: 800, height: 560 }}>
      {children as never}
    </div>
  );
}

export function StanceLensPopulated() {
  return (
    <Frame>
      <DeckGLMap
        snapshot={makeSnapshot()}
        mapData={mapDataWith(BALKANIZATION)}
        lens={{ kind: "stance" }}
      />
    </Frame>
  );
}

export function HeatLensRamp() {
  return (
    <Frame>
      <DeckGLMap snapshot={makeSnapshot()} mapData={null} lens={{ kind: "heat" }} />
    </Frame>
  );
}

export function FactionLensWithPicker() {
  return (
    <Frame>
      <DeckGLMap
        snapshot={makeSnapshot()}
        mapData={mapDataWith(BALKANIZATION)}
        lens={{ kind: "faction" }}
        factionFilter="FAC_NEW_AFRIKAN_UNITY"
      />
    </Frame>
  );
}

export function HonestNoBalkanizationData() {
  return (
    <Frame>
      <DeckGLMap snapshot={makeSnapshot()} mapData={null} lens={{ kind: "stance" }} />
    </Frame>
  );
}
