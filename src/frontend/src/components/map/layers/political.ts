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
 * STRIPE lane (Wave 4, DESIGN_BIBLE.md §2.1 layer 3 + §6): contested counties now render
 * with a TRUE diagonal-stripe fill (the CK3 hatch convention), replacing the earlier
 * desaturated-fill-plus-outline proxy. The hatch is drawn by `@deck.gl/extensions`'
 * `FillStyleExtension` — already a dependency — masked against a generated PNG atlas from
 * `./stripePattern` (no binary asset). A gold contest border is kept over the hatch.
 *
 * SHIMMER lane (Wave 4, DESIGN_BIBLE.md §2.2 "geometry never animates; claims do"): the
 * polity fill + claim-border layers carry a deck-native attribute `transitions` block, so
 * when a claim's `memberFips` changes between snapshots the re-dissolved fill/border
 * settles over `BORDER_REDRAW_MS` (≥600 ms) instead of snapping. This is the only
 * render-path animation the integration ledger's performance budget permits ("nothing
 * animates on the deck.gl render path except deck-native layer transitions") — there is no
 * per-frame time uniform and no CSS over the canvas (the `.claim-shimmer` keyframe in
 * index.css stays for DOM chrome / the wire toast only). The redraw is made ATTRIBUTABLE
 * via `PolityClaim.redrawCause`: when set, the border renders in the gold redraw accent and
 * the cause is threaded into the layer `updateTriggers`, so a future wire headline can name
 * WHY a border moved (the wire wiring itself is out of this lane's scope — see the
 * `redrawCause` seam comment at the border layer). `DeckGLMap`'s existing call site is
 * unchanged: `redrawCause` is optional and absent claims render exactly as before.
 *
 * DEVIATION: "de facto != de jure" contest detection has no de jure baseline available to
 * a pure function with these inputs, so a county is treated as contested when it appears in
 * more than one claim's `memberFips` (an overlap proxy computable purely from the given
 * claims) — Lane B/D may replace this with a real de-jure-baseline signal once that data
 * reaches the client; the caller can always pass `showContested: false` to suppress this
 * layer entirely in the meantime.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { FillStyleExtension, type FillStyleExtensionProps } from "@deck.gl/extensions";
import { membershipKey, mergePolity, mergePolityOutline } from "@/lib/geo/polity";
import {
  STRIPE_PATTERN_MAPPING,
  STRIPE_PATTERN_NAME,
  STRIPE_PATTERN_SCALE,
  stripePatternAtlas,
} from "./stripePattern";
import type {
  CountyFeatureCollection,
  CountyProperties,
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
  /**
   * Optional cause of the most recent membership change (e.g. `"liberation:detroit"`),
   * for the SHIMMER seam (see module docstring). When set, the claim border renders in the
   * gold redraw accent and the cause is threaded into `updateTriggers` so a future wire
   * headline can name why the border moved. Absent/null ⇒ a settled claim, rendered plain.
   */
  redrawCause?: string | null;
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

// Contested-county styling: the diagonal hatch is masked from `stripePattern`, so
// CONTESTED_FILL supplies only the hatch COLOUR (a warm warning grey-gold) — the
// FillStyleExtension mask carves the stripes out of it. The alpha is raised vs the old
// flat-fill proxy because ~half the pixels are now transparent gaps. CONTESTED_BORDER is
// the gold contest outline kept over the hatch.
const CONTESTED_FILL: RGBAColor = [140, 120, 70, 150];
const CONTESTED_BORDER: RGBAColor = [220, 200, 90, 200];

// SHIMMER lane. Deck-native transition duration for a claim re-dissolve; ≥600 ms per
// DESIGN_BIBLE.md §2.2 / §6 ("600ms+ for meaning-bearing transitions").
const BORDER_REDRAW_MS = 650;
// Gold redraw accent — the map-side echo of the index.css `.claim-shimmer` gold sweep,
// applied to a border whose claim carries a `redrawCause` (see module docstring).
const CLAIM_REDRAW_ACCENT: RGBAColor = [230, 200, 96, 255];

/** Border colour for a claim: the gold redraw accent while a redraw cause is live, else
 * the claim's own colour. The `transitions` block below tweens between them, so clearing
 * `redrawCause` on the next snapshot produces the ≥650 ms gold-to-claim shimmer settle. */
function borderColor(claim: PolityClaim): RGBAColor {
  return claim.redrawCause ? CLAIM_REDRAW_ACCENT : claim.color;
}

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
  // SHIMMER: `membershipKey` is the stable signature of who this polity holds — when a
  // county changes hands the string changes, deck.gl re-evaluates the fill accessor, and
  // the `transitions` block below settles the re-dissolved fill over ≥650 ms. `redrawCause`
  // rides along so the trigger fires (and is inspectable) even when only the cause changes.
  const membershipSig = membershipKey(claim.memberFips);
  return new GeoJsonLayer({
    id: `political-polity-fill-${claim.polityId}`,
    data: fill,
    pickable: false,
    filled: true,
    stroked: false,
    getFillColor: claim.color,
    updateTriggers: { getFillColor: [claim.color, membershipSig, claim.redrawCause ?? null] },
    transitions: { getFillColor: BORDER_REDRAW_MS },
  });
}

function buildPolityBorderLayer(topology: CountyTopology, claim: PolityClaim): GeoJsonLayer {
  const outline = mergePolityOutline(topology, claim.memberFips);
  const membershipSig = membershipKey(claim.memberFips);
  // SHIMMER SEAM (wire integration OUT of scope): `redrawCause` is exposed in this layer's
  // `updateTriggers` so a future WireHeadline consumer can read the cause of a border move
  // and name it ("Detroit liberated"). When set, `borderColor` returns the gold accent; the
  // `getLineColor` transition then tweens gold → claim colour as the cause clears next tick.
  return new GeoJsonLayer({
    id: `political-polity-border-${claim.polityId}`,
    data: outline,
    pickable: false,
    filled: false,
    stroked: true,
    getLineColor: borderColor(claim),
    lineWidthUnits: "pixels",
    getLineWidth: 3,
    lineWidthMinPixels: 2,
    updateTriggers: {
      getLineColor: [borderColor(claim), membershipSig, claim.redrawCause ?? null],
    },
    transitions: { getLineColor: BORDER_REDRAW_MS, getLineWidth: BORDER_REDRAW_MS },
  });
}

function buildContestedLayer(
  counties: CountyFeatureCollection,
  contestedFips: Set<string>,
): GeoJsonLayer {
  const contestedFeatures = counties.features.filter((f) => contestedFips.has(f.properties.GEOID));
  // STRIPE: FillStyleExtension tiles the fill with the generated diagonal-hatch atlas.
  // `fillPatternMask` (default true) uses the atlas ALPHA as a stencil and keeps
  // `getFillColor` for the hatch colour, so the stripes read in the warning grey-gold over
  // whatever polity fill lies beneath (see stripePattern.ts for the mask/world-size proof).
  return new GeoJsonLayer<CountyProperties, FillStyleExtensionProps>({
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
    extensions: [new FillStyleExtension({ pattern: true })],
    fillPatternAtlas: stripePatternAtlas(),
    fillPatternMapping: STRIPE_PATTERN_MAPPING,
    fillPatternMask: true,
    getFillPattern: () => STRIPE_PATTERN_NAME,
    getFillPatternScale: STRIPE_PATTERN_SCALE,
    updateTriggers: {
      getFillColor: contestedFips.size,
      getLineColor: contestedFips.size,
      getFillPattern: contestedFips.size,
    },
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
