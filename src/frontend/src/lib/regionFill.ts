/**
 * regionFillForLens — pure function mapping a map `Lens` + an aggregated
 * region feature's properties to an RGBA fill color, or `null` for an
 * honest empty/neutral fill (Constitution III.11: never a fabricated
 * default).
 *
 * Counterpart to `mapLensLayers.ts`'s per-hex `buildLensLayers`, but for
 * aggregated (county/cz/msa/bea_ea/state) region features — those don't
 * carry the hex-native balkanization detail (per-faction influence,
 * `dominant_faction_id`) the ring/hull overlays read, so several lenses
 * degrade here:
 *
 * - `heat`: the heat ramp over `properties.heat`, normalized against the
 *   caller-supplied `{min, max}` domain (aggregated heat has no fixed
 *   [0, 1] range).
 * - `habitability`: the biocapacity ramp (`lensRampStops`'s own choice for
 *   this lens) sampled directly at `properties.habitability` — already a
 *   population-weighted mean in ~[0, 1] (`sampleRampStops` clamps), so no
 *   domain division needed, unlike heat/metric. Null-honest: a
 *   partial-coverage group reports `habitability: null`
 *   (`_aggregate_hex_features`), never a fabricated 0.
 * - `metric`: `properties[metric]` via that metric's own ramp
 *   (`lensRampStops` + `sampleRampStops`, reused — never duplicated here),
 *   normalized against the same domain as heat.
 * - `stance`: FLAGGED FOR OWNER REVIEW. The hex-native stance lens colors
 *   by dominant faction (`mapLensLayers.ts`'s `buildLensLayers` +
 *   `territory_influence`); there is no region-level equivalent aggregate.
 *   This falls back to the consciousness ramp over an aggregate
 *   `consciousness` value, but `_aggregate_hex_features`
 *   (`web/game/engine_bridge.py`) does not currently emit one on real
 *   `/map/` payloads — null-honest until the backend grows that aggregate
 *   or the owner picks a different region-level stance proxy.
 * - `faction` / `collapse`: always `null` (neutral fill) — these are
 *   hex-native ring/hull overlays (Constitution VIII.9: sovereign CLAIMS
 *   only), which remain the actual signal at every framing; a region fill
 *   would either be misleading (no per-faction breakdown to summarize) or
 *   duplicate information the overlay already carries.
 * - `class_composition` (spec-113 Lane B/D): `properties.dominant_class`
 *   (the group's population-weighted plurality `SocialRole`,
 *   `_aggregate_hex_features`'s `dominant_class_pop` vote) via the SAME
 *   `SOCIAL_ROLE_COLOR` palette `mapLensLayers.ts`'s hex-native fill uses —
 *   one source of truth, no duplicated color table. Null-honest for an
 *   absent/unrecognized role.
 */

import { lensRampStops, sampleRampStops, type Lens, type MapMetric } from "@/lib/lens";
import { rampForLayer, type RGBAColor } from "@/theme/colors";
import { SOCIAL_ROLE_COLOR } from "@/components/map/mapLensLayers";

/** The value range a domain-normalized field (heat, `{kind:"metric"}`) is scaled against. */
export interface FillDomain {
  min: number;
  max: number;
}

/**
 * The subset of an aggregated region feature's properties this module
 * reads. Deliberately NOT `AdminFeatureProperties` (`types/game.ts`): that
 * interface's `consciousness`/`wealth`/`rent`/`biocapacity`/`cz_id`/
 * `cz_name`/`bea_ea_code`/`bea_ea_name`/`msa_code`/`msa_name`/
 * `county_fips`/`state_fips`/`state_name` fields do not match what
 * `_aggregate_hex_features` (`web/game/engine_bridge.py`) actually emits
 * today (`group_key`/`group_name`/`hex_count`/`member_h3`/`heat`/
 * `habitability`/`population`/`profit_rate`/`exploitation_rate`/`occ`/
 * `imperial_rent`/`org_presence`) — flagged for the owner queue, out of
 * this lane's scope to reconcile. `consciousness` is kept here (optional)
 * only for the stance branch above, which is itself flagged.
 */
export type RegionFillProperties = Partial<Record<MapMetric, number | null>> & {
  consciousness?: number | null;
  /**
   * Spec-113 Lane D's aggregated `dominant_class` (the population-weighted
   * plurality `SocialRole` across the group's members,
   * `_aggregate_hex_features`'s `dominant_class_pop` vote) — categorical,
   * so (like `RegionFillProperties` itself vs. `MapMetric`) it lives
   * outside the numeric bag.
   */
  dominant_class?: string | null;
};

/** True for a real, finite value — false for `null`/`undefined`/`NaN`. */
function isPresent(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && Number.isFinite(value);
}

/** Normalize `value` into [0, 1] against `domain`; `null` when absent/non-finite. */
function normalize(value: number | null | undefined, domain: FillDomain): number | null {
  if (!isPresent(value)) {
    return null;
  }
  const span = domain.max - domain.min;
  if (span <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(1, (value - domain.min) / span));
}

/** Shared by the `heat`/`metric` cases: ramp-sample a domain-normalized value, or `null` if either is absent. */
function normalizedRampFill(
  lens: Lens,
  value: number | null | undefined,
  domain: FillDomain,
): RGBAColor | null {
  const ramp = lensRampStops(lens);
  const t = normalize(value, domain);
  return ramp === null || t === null ? null : sampleRampStops(ramp, t);
}

/** The `stance` case: `properties.consciousness` sampled over the consciousness ramp (FLAGGED, see module docstring). */
function stanceFill(properties: RegionFillProperties): RGBAColor | null {
  return isPresent(properties.consciousness)
    ? sampleRampStops(rampForLayer("consciousness"), properties.consciousness)
    : null;
}

/**
 * Resolve the fill color for one aggregated region feature under the
 * active lens, or `null` for an honest empty/neutral fill.
 */
export function regionFillForLens(
  lens: Lens,
  properties: RegionFillProperties,
  domain: FillDomain,
): RGBAColor | null {
  switch (lens.kind) {
    case "heat":
      return normalizedRampFill(lens, properties.heat, domain);
    case "habitability": {
      const ramp = lensRampStops(lens);
      if (ramp === null || !isPresent(properties.habitability)) {
        return null;
      }
      return sampleRampStops(ramp, properties.habitability);
    }
    case "metric":
      return normalizedRampFill(lens, properties[lens.metric], domain);
    case "stance":
      return stanceFill(properties);
    case "faction":
    case "collapse":
      return null;
    case "class_composition": {
      const role = properties.dominant_class;
      return role ? (SOCIAL_ROLE_COLOR[role] ?? null) : null;
    }
  }
}
