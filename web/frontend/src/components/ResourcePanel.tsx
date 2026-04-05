/**
 * Vanguard Economy resource panel.
 *
 * Displays CL, SL, REP, Budget, and Heat as a compact resource bar.
 * Updates each tick from the player org's vanguard resources.
 */

import type { OrgState } from "@/types/game";

interface ResourcePanelProps {
  playerOrg: OrgState | null;
}

/** Compact resource bar with progress indicators. */
export function ResourcePanel({ playerOrg }: ResourcePanelProps) {
  if (!playerOrg) {
    return (
      <div className="rounded-lg border border-wet-concrete bg-dark-metal p-3 text-center text-sm text-ash">
        No player organization
      </div>
    );
  }

  const v = playerOrg.vanguard;

  let heatColor = "var(--color-bone, #e8e0d0)";
  if (v) {
    if (v.heat > 0.6) {
      heatColor = "var(--color-phosphor-red, #ff4040)";
    } else if (v.heat > 0.3) {
      heatColor = "var(--color-gold, #c8a860)";
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-wet-concrete bg-dark-metal p-3">
      {/* Org header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gold">{playerOrg.name}</span>
        <span className="text-[10px] uppercase tracking-wider text-ash">{playerOrg.org_type}</span>
      </div>

      {v ? (
        <div className="grid grid-cols-5 gap-2">
          <ResourceGauge
            label="CL"
            tooltip="Cadre Labor — skilled organizer hours"
            value={v.cadre_labor}
            max={v.max_cadre_labor}
            color="var(--color-royal-blue, #4a7cff)"
          />
          <ResourceGauge
            label="SL"
            tooltip="Sympathizer Labor — mass supporter hours"
            value={v.sympathizer_labor}
            max={v.max_sympathizer_labor}
            color="var(--color-data-green, #50c878)"
          />
          <ResourceStat
            label="REP"
            tooltip="Reputation — social capital"
            value={`${(v.reputation * 100).toFixed(0)}%`}
            color={
              v.reputation > 0.5 ? "var(--color-data-green, #50c878)" : "var(--color-bone, #e8e0d0)"
            }
          />
          <ResourceStat
            label="$$$"
            tooltip="Budget — cash on hand"
            value={`$${v.budget.toFixed(0)}`}
            color="var(--color-gold, #c8a860)"
          />
          <ResourceStat
            label="HEAT"
            tooltip="State attention — higher = more danger"
            value={`${(v.heat * 100).toFixed(0)}%`}
            color={heatColor}
          />
        </div>
      ) : (
        /* Fallback for orgs without vanguard resources */
        <div className="grid grid-cols-3 gap-2">
          <ResourceStat
            label="Budget"
            value={`$${playerOrg.budget.toFixed(0)}`}
            color="var(--color-gold, #c8a860)"
          />
          <ResourceStat
            label="Cadre"
            value={playerOrg.cadre_level.toFixed(2)}
            color="var(--color-royal-blue, #4a7cff)"
          />
          <ResourceStat
            label="Heat"
            value={`${(playerOrg.heat * 100).toFixed(0)}%`}
            color="var(--color-bone, #e8e0d0)"
          />
        </div>
      )}
    </div>
  );
}

/** Gauge with fill bar for resources that have a max. */
function ResourceGauge({
  label,
  tooltip,
  value,
  max,
  color,
}: {
  label: string;
  tooltip?: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex flex-col gap-0.5" title={tooltip}>
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
        <span className="font-mono text-xs font-semibold" style={{ color }}>
          {value.toFixed(1)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-void">
        <div
          className="h-full rounded-full transition-[width] duration-300"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/** Simple stat display for resources without a max. */
function ResourceStat({
  label,
  tooltip,
  value,
  color,
}: {
  label: string;
  tooltip?: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center gap-0.5" title={tooltip}>
      <span className="text-[10px] uppercase tracking-wider text-ash">{label}</span>
      <span className="font-mono text-sm font-semibold" style={{ color }}>
        {value}
      </span>
    </div>
  );
}
