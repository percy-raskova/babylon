/**
 * MapLegend v2 (spec-113 Lane B, architecture §3.3, DESIGN_BIBLE.md §3.2).
 *
 * Renders from a `MapLensDef.legend` spec (`@/lib/lenses/registry`) instead
 * of deriving directly from a `Lens` value — gains a categorical swatch mode
 * (stance/faction/collapse/class_composition finally get a real legend
 * instead of just the `lens-legend-label` text chip DeckGLMap already
 * renders) alongside the existing ramp mode. `legend.kind === "none"`
 * renders nothing, same as the old "no ramp for this lens" behavior.
 *
 * `currentValue` (ramp mode only, normalized to the SAME [0,1] the ramp
 * itself is sampled at) draws a tick marking where the current world state
 * sits on the ramp (bible §3.2's Sylvester citation: "legend shows a marker
 * for where the current world state sits"); omitted/`null` when the caller
 * has no honest summary value yet (Constitution III.11 — no marker beats a
 * fabricated one). `flash` (bible §3.2/§6: "no silent rescale... domain
 * changes fire a legend flash") briefly highlights the ramp when the
 * caller's domain memo (`lib/lenses/domainMemo.ts`) reports the underlying
 * data outgrew the fixed domain.
 */

import { sampleRampStops } from "@/lib/lens";
import { rgbaToCss } from "@/theme/colors";
import type { LensLegend } from "@/lib/lenses/registry";

const LEGEND_STEPS = 8;

interface MapLegendProps {
  legend: LensLegend;
  /** Human-readable legend text — usually `MapLensDef.label` or the existing `lensLegendLabel(lens)`. */
  label: string;
  /** Ramp mode only: normalized [0,1] position of the current world-state value, or `null`/omitted for none. */
  currentValue?: number | null;
  /** Ramp mode only: true for one render after the domain memo reports a would-be rescale. */
  flash?: boolean;
}

export function MapLegend({ legend, label, currentValue = null, flash = false }: MapLegendProps) {
  if (legend.kind === "none") return null;

  if (legend.kind === "categorical") {
    return (
      <div className="flex flex-col gap-1" data-testid="map-legend" data-legend-kind="categorical">
        <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
        <div className="flex flex-col gap-0.5">
          {legend.entries.map((entry) => (
            <div key={entry.label} className="flex items-center gap-1.5">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ backgroundColor: rgbaToCss(entry.color) }}
              />
              <span className="text-[10px] text-fog">{entry.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const swatches = Array.from({ length: LEGEND_STEPS }, (_, i) => {
    const t = i / (LEGEND_STEPS - 1);
    return { t, color: rgbaToCss(sampleRampStops(legend.stops, t)) };
  });
  const markerLeftPct =
    currentValue != null && Number.isFinite(currentValue)
      ? `${Math.max(0, Math.min(1, currentValue)) * 100}%`
      : null;

  return (
    <div
      className={`flex items-center gap-2 ${flash ? "animate-pulse" : ""}`}
      data-testid="map-legend"
      data-legend-kind="ramp"
      data-flash={flash ? "true" : "false"}
    >
      <span className="text-[10px] text-ash">0</span>
      <div className="relative flex h-3 w-32 overflow-hidden rounded-sm">
        {swatches.map((swatch, i) => (
          <div key={i} className="flex-1" style={{ backgroundColor: swatch.color }} />
        ))}
        {markerLeftPct !== null && (
          <div
            data-testid="map-legend-marker"
            className="absolute top-0 h-full w-[2px] -translate-x-1/2 bg-bone"
            style={{ left: markerLeftPct }}
          />
        )}
      </div>
      <span className="text-[10px] text-ash">1</span>
      <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
    </div>
  );
}
