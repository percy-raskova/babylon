/**
 * Persistent indicators — always-visible summary metrics in the top bar.
 *
 * Shows 4 key derived values from the current snapshot.
 */

import type { GameSnapshot } from "@/types/game";

interface PersistentIndicatorsProps {
  snapshot: GameSnapshot;
}

export function PersistentIndicators({
  snapshot,
}: PersistentIndicatorsProps) {
  const { entities, territories, organizations, edges } = snapshot;

  const avgHeat =
    territories.length > 0
      ? territories.reduce((s, t) => s + t.heat, 0) / territories.length
      : 0;

  const avgConsciousness =
    entities.length > 0
      ? entities.reduce((s, e) => s + e.consciousness, 0) / entities.length
      : 0;

  const solidarityEdges = edges.filter(
    (e) => e.solidarity_strength > 0,
  ).length;

  return (
    <div className="flex items-center gap-4">
      <Indicator label="Heat" value={avgHeat} color="text-phosphor-red" />
      <Indicator
        label="Consciousness"
        value={avgConsciousness}
        color="text-royal-blue"
      />
      <Indicator
        label="Orgs"
        value={organizations.length}
        color="text-grow-purple"
        integer
      />
      <Indicator
        label="Solidarity"
        value={solidarityEdges}
        color="text-data-green"
        integer
      />
    </div>
  );
}

function Indicator({
  label,
  value,
  color,
  integer = false,
}: {
  label: string;
  value: number;
  color: string;
  integer?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-ash">
        {label}
      </span>
      <span className={`font-mono text-sm font-semibold ${color}`}>
        {integer ? value : value.toFixed(2)}
      </span>
    </div>
  );
}
