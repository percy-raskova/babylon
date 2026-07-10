/**
 * MapLegend preview — the ramp swatch strip for metric/heat/habitability
 * lenses. Renders `null` for the three balkanization-derived lenses
 * (stance/faction/collapse) by design — DeckGLMap's sibling legend-label
 * text covers those instead. Pure props (lens), no store.
 */
import { MapLegend } from "babylon-cockpit";

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[380px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="flex items-center bg-void p-3" style={{ width: 380 }}>
      {children as never}
    </div>
  );
}

export function HeatRamp() {
  return (
    <Frame>
      <MapLegend lens={{ kind: "heat" }} />
    </Frame>
  );
}

export function HabitabilityRamp() {
  return (
    <Frame>
      <MapLegend lens={{ kind: "habitability" }} />
    </Frame>
  );
}

export function MetricRampProfitRate() {
  return (
    <Frame>
      <MapLegend lens={{ kind: "metric", metric: "profit_rate" }} />
    </Frame>
  );
}

/**
 * Honest-empty: balkanization-derived lenses have no continuous ramp, so
 * MapLegend returns null here — the caption is this preview file's own
 * annotation (outside the component) documenting that the blank space
 * below is the correct, designed render, not a capture failure.
 */
export function NoRampForBalkanizationLens() {
  return (
    <Frame>
      <span className="text-[10px] italic text-shroud">
        (MapLegend renders null for lens.kind="stance" — DeckGLMap's legend-label text covers it)
      </span>
      <MapLegend lens={{ kind: "stance" }} />
    </Frame>
  );
}
