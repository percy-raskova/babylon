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
  /**
   * Ramp mode only: dim the strip because the lens carries no usable signal this
   * tick (degenerate domain — MapControls' `rampEmpty`). Reads as an inactive
   * scale rather than a live 0→1 nothing sits on (Constitution III.11).
   */
  muted?: boolean;
}

export function MapLegend({
  legend,
  label,
  currentValue = null,
  flash = false,
  muted = false,
}: MapLegendProps) {
  if (legend.kind === "none") return null;

  if (legend.kind === "vector") {
    return (
      <div className="flex flex-col gap-1" data-testid="map-legend" data-legend-kind="vector">
        <span className="text-[10px] uppercase tracking-wider text-ksbc-muted-2">{label}</span>
        <div className="flex items-center gap-1" data-testid="map-legend-vector-key">
          {/* Direction/width key (DESIGN_BIBLE.md §11 law 1: magnitude
              reads as geometry, never a second color) — three bars of
              increasing thickness feeding an arrowhead glyph, all in the
              lens's one fixed hue. */}
          <span
            aria-hidden="true"
            className="h-[2px] w-3"
            style={{ backgroundColor: rgbaToCss(legend.color) }}
          />
          <span
            aria-hidden="true"
            className="h-[3px] w-4"
            style={{ backgroundColor: rgbaToCss(legend.color) }}
          />
          <span
            aria-hidden="true"
            className="h-1 w-5"
            style={{ backgroundColor: rgbaToCss(legend.color) }}
          />
          <span
            aria-hidden="true"
            className="text-xs leading-none"
            style={{ color: rgbaToCss(legend.color) }}
          >
            →
          </span>
        </div>
        <span className="max-w-[220px] text-[10px] text-ink">{legend.description}</span>
      </div>
    );
  }

  if (legend.kind === "categorical") {
    return (
      <div className="flex flex-col gap-1" data-testid="map-legend" data-legend-kind="categorical">
        <span className="text-[10px] uppercase tracking-wider text-ksbc-muted-2">{label}</span>
        <div className="flex flex-col gap-0.5">
          {legend.entries.map((entry) => (
            <div key={entry.label} className="flex items-center gap-1.5">
              <span
                className="h-2.5 w-2.5 shrink-0 border border-key-shadow"
                style={{ backgroundColor: rgbaToCss(entry.color) }}
              />
              <span className="text-[10px] text-ink">{entry.label}</span>
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
      className={`flex items-center gap-2 ${flash ? "legend-flash" : ""} ${muted ? "opacity-50" : ""}`}
      data-testid="map-legend"
      data-legend-kind="ramp"
      data-flash={flash ? "true" : "false"}
      data-muted={muted ? "true" : "false"}
    >
      <span className="text-[10px] text-ksbc-muted-2">0</span>
      <div className="relative flex h-3 w-32 overflow-hidden border border-key-shadow">
        {swatches.map((swatch, i) => (
          <div key={i} className="flex-1" style={{ backgroundColor: swatch.color }} />
        ))}
        {markerLeftPct !== null && (
          <div
            data-testid="map-legend-marker"
            className="absolute top-0 h-full w-[2px] -translate-x-1/2 bg-accent-gold"
            style={{ left: markerLeftPct }}
          />
        )}
      </div>
      <span className="text-[10px] text-ksbc-muted-2">1</span>
      <span className="text-[10px] uppercase tracking-wider text-ksbc-muted-2">{label}</span>
    </div>
  );
}
