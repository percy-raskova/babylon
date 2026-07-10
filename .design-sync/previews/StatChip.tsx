/**
 * StatChip preview — ported from the canonical StatusBar composition
 * (src/components/shell/StatusBar.tsx): the three top-bar metric chips,
 * plus the Constitution III.11 honest no-data state.
 */
import { StatChip } from "babylon-cockpit";

export function StatusBarMetrics() {
  return (
    <div className="flex items-center gap-2 bg-void p-4">
      <StatChip
        label="Profit"
        value={0.142}
        format={(v: number) => v.toFixed(3)}
        colorClassName="text-rupture"
      />
      <StatChip
        label="Rent Φ"
        value={84213907.42}
        format={(v: number) => v.toFixed(2)}
        colorClassName="text-rent"
      />
      <StatChip
        label="Pop"
        value={1793561}
        format={(v: number) => v.toLocaleString()}
        colorClassName="text-population"
      />
    </div>
  );
}

export function HonestNoData() {
  return (
    <div className="flex items-center gap-2 bg-void p-4">
      <StatChip
        label="Profit"
        value={null}
        format={(v: number) => v.toFixed(3)}
        colorClassName="text-rupture"
      />
      <StatChip
        label="Gamma"
        value={undefined}
        format={(v: number) => v.toFixed(2)}
        colorClassName="text-spire"
      />
    </div>
  );
}
