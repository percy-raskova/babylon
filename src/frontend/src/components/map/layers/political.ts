/**
 * political.ts — the political cartography layer stack (Lane Carto, spec-113 §7;
 * DESIGN_BIBLE.md §2.1 layers 1-3). Authored by Lane Carto before Lane B branches; this
 * is the FROZEN export Lane B consumes to compose the map (same pattern as Lane A's
 * stub-file rule) — Lane B wires store state into `BuildPoliticalLayersOptions`, this
 * module stays a pure function with no store imports.
 *
 * Renders the immutable de jure county/state mesh (bible layer 1, hairline borders) plus
 * de facto polity fills and thick claim borders dissolved client-side from `PolityClaim`
 * membership via `lib/geo/polity.ts` (bible layer 2), plus a contested-county overlay
 * (bible layer 3). Lens recoloring (bible layer 4) and flows/markers (layer 5) are NOT
 * this module's concern — `MapLensBar`'s active lens recolors on top, per Lane B.
 *
 * DEVIATION from architecture.md §7's literal `buildPoliticalLayers` signature
 * (`{counties, states, claims, showContested}`, no topology field): a `topology:
 * CountyTopology` field was added. Without the raw shared-arc topology, "de-facto polity
 * fills + thick claim borders (from mergePolity output)" is not computable — `PolityClaim`
 * only carries `memberFips` (no precomputed geometry), and `mergePolity`/
 * `mergePolityOutline` require topojson-client's shared-arc structure, which a plain
 * GeoJSON `FeatureCollection` (already-extracted via `countyFeatures()`) has lost. This
 * keeps the function pure/synchronous rather than pushing an async topology fetch inside
 * it, and Lane B already has the topology in hand (it drives `MapLensBar`'s framing and
 * therefore already loads `lib/geo/topology.ts`).
 *
 * DEVIATION (noted per the architecture's own escape hatch — "true striping deferred to
 * the design phase — note it"): contested counties render as a distinct desaturated fill
 * + differently-colored border, not a true dashed/hatched stroke — `GeoJsonLayer` has no
 * native dash support (that needs `@deck.gl/extensions`' `PathStyleExtension`, a new
 * dependency outside this lane's package.json ownership, which is scoped to
 * `topojson-client` only). Also DEVIATION: "de facto != de jure" contest detection has no
 * de jure baseline available to a pure function with these inputs, so a county is treated
 * as contested when it appears in more than one claim's `memberFips` (an overlap proxy
 * computable purely from the given claims) — Lane B/D may replace this with a real
 * de-jure-baseline signal once that data reaches the client; the caller can always pass
 * `showContested: false` to suppress this layer entirely in the meantime.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { mergePolity, mergePolityOutline } from "@/lib/geo/polity";
import type {
  CountyFeatureCollection,
  CountyTopology,
  StateFeatureCollection,
} from "@/lib/geo/topology";
import type { RGBAColor } from "@/theme/colors";

/** A de facto political claim: a named polity and the counties it currently controls. */
export interface PolityClaim {
  polityId: string;
  name: string;
  color: RGBAColor;
  memberFips: string[];
}

export interface BuildPoliticalLayersOptions {
  /** Raw county topology — the shared-arc source for both the hairline base layer and
   * every claim's `mergePolity`/`mergePolityOutline` dissolve. See module docstring. */
  topology: CountyTopology;
  counties: CountyFeatureCollection;
  states: StateFeatureCollection;
  claims?: PolityClaim[];
  showContested?: boolean;
}

// ---------------------------------------------------------------------------
// Color/alpha budget (DESIGN_BIBLE.md §6: "grids/borders... at 20-30% the alpha of the
// data they host"). County hairlines are pure structure (bible layer 1, "immutable")
// and sit at the low end; state borders are "heavier" (bible §2.1) since they carry the
// colonial-baseline register the addendum names explicitly.
// ---------------------------------------------------------------------------

const COUNTY_HAIRLINE_ALPHA = 64; // ~25% of 255, within the 20-30% band
const STATE_BORDER_ALPHA = 115; // ~45% of 255 — "heavier" than county hairlines

const COUNTY_HAIRLINE_COLOR: RGBAColor = [180, 184, 196, COUNTY_HAIRLINE_ALPHA];
const STATE_BORDER_COLOR: RGBAColor = [180, 184, 196, STATE_BORDER_ALPHA];

// Contested-county proxy styling (dash deferred — see module docstring).
const CONTESTED_FILL: RGBAColor = [90, 90, 96, 90];
const CONTESTED_BORDER: RGBAColor = [220, 200, 90, 200];

/** Counties claimed by more than one polity — the computable proxy for "contested". */
function computeContestedFips(claims: PolityClaim[]): Set<string> {
  const counts = new Map<string, number>();
  for (const claim of claims) {
    for (const fips of claim.memberFips) {
      counts.set(fips, (counts.get(fips) ?? 0) + 1);
    }
  }
  const contested = new Set<string>();
  for (const [fips, count] of counts) {
    if (count > 1) {
      contested.add(fips);
    }
  }
  return contested;
}

function buildCountyHairlineLayer(counties: CountyFeatureCollection): GeoJsonLayer {
  return new GeoJsonLayer({
    id: "political-county-hairlines",
    data: counties,
    pickable: false,
    filled: false,
    stroked: true,
    getLineColor: COUNTY_HAIRLINE_COLOR,
    lineWidthUnits: "pixels",
    getLineWidth: 1,
    lineWidthMinPixels: 1,
    updateTriggers: { getLineColor: COUNTY_HAIRLINE_ALPHA },
  });
}

function buildStateBorderLayer(states: StateFeatureCollection): GeoJsonLayer {
  return new GeoJsonLayer({
    id: "political-state-borders",
    data: states,
    pickable: false,
    filled: false,
    stroked: true,
    getLineColor: STATE_BORDER_COLOR,
    lineWidthUnits: "pixels",
    getLineWidth: 2,
    lineWidthMinPixels: 1.5,
    updateTriggers: { getLineColor: STATE_BORDER_ALPHA },
  });
}

function buildPolityFillLayer(topology: CountyTopology, claim: PolityClaim): GeoJsonLayer {
  const fill = mergePolity(topology, claim.memberFips);
  return new GeoJsonLayer({
    id: `political-polity-fill-${claim.polityId}`,
    data: fill,
    pickable: false,
    filled: true,
    stroked: false,
    getFillColor: claim.color,
    updateTriggers: { getFillColor: claim.color },
  });
}

function buildPolityBorderLayer(topology: CountyTopology, claim: PolityClaim): GeoJsonLayer {
  const outline = mergePolityOutline(topology, claim.memberFips);
  return new GeoJsonLayer({
    id: `political-polity-border-${claim.polityId}`,
    data: outline,
    pickable: false,
    filled: false,
    stroked: true,
    getLineColor: claim.color,
    lineWidthUnits: "pixels",
    getLineWidth: 3,
    lineWidthMinPixels: 2,
    updateTriggers: { getLineColor: claim.color },
  });
}

function buildContestedLayer(
  counties: CountyFeatureCollection,
  contestedFips: Set<string>,
): GeoJsonLayer {
  const contestedFeatures = counties.features.filter((f) => contestedFips.has(f.properties.GEOID));
  return new GeoJsonLayer({
    id: "political-contested-counties",
    data: { type: "FeatureCollection", features: contestedFeatures },
    pickable: false,
    filled: true,
    stroked: true,
    getFillColor: CONTESTED_FILL,
    getLineColor: CONTESTED_BORDER,
    lineWidthUnits: "pixels",
    getLineWidth: 2,
    lineWidthMinPixels: 1.5,
    updateTriggers: { getFillColor: contestedFips.size, getLineColor: contestedFips.size },
  });
}

/**
 * Build the political cartography deck.gl layer stack: de jure county hairlines + state
 * borders (bottom), de facto polity fills + claim borders per `claims` (middle),
 * contested-county overlay (top, optional). Array order is bottom-to-top render order.
 */
export function buildPoliticalLayers(opts: BuildPoliticalLayersOptions): GeoJsonLayer[] {
  const { topology, counties, states, claims = [], showContested = true } = opts;
  const layers: GeoJsonLayer[] = [
    buildCountyHairlineLayer(counties),
    buildStateBorderLayer(states),
  ];

  for (const claim of claims) {
    layers.push(buildPolityFillLayer(topology, claim));
    layers.push(buildPolityBorderLayer(topology, claim));
  }

  if (showContested && claims.length > 0) {
    const contestedFips = computeContestedFips(claims);
    if (contestedFips.size > 0) {
      layers.push(buildContestedLayer(counties, contestedFips));
    }
  }

  return layers;
}
