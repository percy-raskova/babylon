/**
 * Org consciousness distribution — null-honesty per Constitution III.11
 * (`consciousness: null` means the engine hasn't computed a distribution
 * for this org yet; render "no data", never a fabricated thirds split).
 */

import type { ConsciousnessVector } from "@/types/game";

interface ConsciousnessBreakdownProps {
  consciousness: ConsciousnessVector | null;
}

export function ConsciousnessBreakdown({
  consciousness,
}: ConsciousnessBreakdownProps): React.JSX.Element {
  if (!consciousness) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid="consciousness-no-data">
        Consciousness: no data.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5" data-testid="consciousness-breakdown">
      <Row label="Revolutionary" value={consciousness.revolutionary} colorClassName="text-laser" />
      <Row label="Liberal" value={consciousness.liberal} colorClassName="text-cadre" />
      <Row label="Fascist" value={consciousness.fascist} colorClassName="text-rupture" />
    </div>
  );
}

function Row({
  label,
  value,
  colorClassName,
}: {
  label: string;
  value: number;
  colorClassName: string;
}): React.JSX.Element {
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="text-ash">{label}</span>
      <span className={`font-mono ${colorClassName}`}>{value.toFixed(3)}</span>
    </div>
  );
}
