/**
 * DialecticCard — V2 engine visualization component.
 *
 * Renders a single Dialectic as a card with:
 * - Type badge (CommodityDialectic, etc.)
 * - Principal aspect indicator (A/B)
 * - Weight gauge bar
 * - Pole-specific details (observation fields)
 * - Compact sparkline weight history (when provided)
 *
 * Follows Constitution VII design system (dark, soot/bone palette).
 */

import type { DialecticSnapshot, WeightHistoryPoint } from "@/types/dialectic";

interface DialecticCardProps {
  snapshot: DialecticSnapshot;
  history?: WeightHistoryPoint[];
  onClick?: (id: string) => void;
}

/** Display name mapping for type_tags. */
const TYPE_LABELS: Record<string, string> = {
  CommodityDialectic: "Commodity",
};

/** Color mapping per type_tag. */
const TYPE_COLORS: Record<string, string> = {
  CommodityDialectic: "var(--color-gold, #c8a860)",
};

/** Returns a human-readable label for a dialectic type_tag. */
function typeLabel(typeTag: string): string {
  return TYPE_LABELS[typeTag] ?? typeTag;
}

/** Returns the accent color for a dialectic type_tag. */
function typeColor(typeTag: string): string {
  return TYPE_COLORS[typeTag] ?? "var(--color-royal-blue, #80b0e0)";
}

/** Render a compact inline sparkline of weight history using SVG. */
function WeightSparkline({ points, color }: { points: WeightHistoryPoint[]; color: string }) {
  if (points.length < 2) return null;

  const width = 80;
  const height = 20;
  const maxTick = points[points.length - 1]?.tick ?? 0;
  const minTick = points[0]?.tick ?? 0;
  const range = maxTick - minTick || 1;

  const path = points
    .map((p, i) => {
      const x = ((p.tick - minTick) / range) * width;
      const y = height - p.weight * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="opacity-60">
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

/** Compact key=value detail row. */
function DetailRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex items-baseline justify-between text-xs">
      <span className="uppercase tracking-wider text-ash">{label}</span>
      <span
        className="font-mono font-semibold"
        style={{ color: color ?? "var(--color-bone, #e0e0e0)" }}
      >
        {typeof value === "number" ? value.toFixed(3) : value}
      </span>
    </div>
  );
}

/** Dialectic Card — the fundamental v2 visualization unit. */
export function DialecticCard({ snapshot, history, onClick }: DialecticCardProps) {
  const obs = snapshot.observation;
  const color = typeColor(snapshot.type_tag);
  const pct = (snapshot.weight * 100).toFixed(0);
  const aspectLabel = obs.principal_aspect === "A" ? "Pole A" : "Pole B";

  // Build observation details (filter out standard fields)
  const standardKeys = new Set(["id", "type", "weight", "principal_aspect"]);
  const extraFields = Object.entries(obs).filter(([k]) => !standardKeys.has(k) && obs[k] != null);

  return (
    <div
      className="group relative cursor-pointer rounded-lg border border-wet-concrete bg-dark-metal p-3 transition-all duration-200 hover:border-ash hover:shadow-lg hover:shadow-void/50"
      role="button"
      tabIndex={0}
      onClick={() => onClick?.(snapshot.dialectic_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick?.(snapshot.dialectic_id);
      }}
    >
      {/* Header: type badge + principal aspect */}
      <div className="mb-2 flex items-center justify-between">
        <span
          className="rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest"
          style={{
            backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)`,
            color: color,
          }}
        >
          {typeLabel(snapshot.type_tag)}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-ash">{aspectLabel}</span>
      </div>

      {/* Weight gauge */}
      <div className="mb-2">
        <div className="mb-0.5 flex items-baseline justify-between">
          <span className="text-[10px] uppercase tracking-wider text-ash">Weight</span>
          <span className="font-mono text-xs font-semibold" style={{ color }}>
            {pct}%
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-void">
          <div
            className="h-full rounded-full transition-[width] duration-500 ease-out"
            style={{
              width: `${pct}%`,
              backgroundColor: color,
            }}
          />
        </div>
      </div>

      {/* Sparkline (if history provided) */}
      {history && history.length >= 2 && (
        <div className="mb-2 flex justify-center">
          <WeightSparkline points={history} color={color} />
        </div>
      )}

      {/* Observation details */}
      {extraFields.length > 0 && (
        <div className="flex flex-col gap-0.5 border-t border-wet-concrete pt-1.5">
          {extraFields.map(([key, val]) => (
            <DetailRow key={key} label={key} value={val as string | number} color={color} />
          ))}
        </div>
      )}

      {/* Tick + ID footer */}
      <div className="mt-1.5 flex items-center justify-between text-[9px] text-ash opacity-50 group-hover:opacity-80 transition-opacity">
        <span>t={snapshot.tick}</span>
        <span className="font-mono">{snapshot.dialectic_id.slice(0, 8)}</span>
      </div>
    </div>
  );
}
