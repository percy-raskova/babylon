/**
 * BblData preview — monospace data readout (tick counters, currency,
 * percentages). Pure props, no store.
 */
import { BblData } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="flex items-center gap-4 bg-void p-4">{children as never}</div>;
}

export function TickCounter() {
  return (
    <Frame>
      <BblData color="var(--babylon-spire)" size={14}>
        104
      </BblData>
    </Frame>
  );
}

export function ImperialRentReadout() {
  return (
    <Frame>
      <BblData color="var(--babylon-rent)" size={16}>
        Φ 84,213,907.42
      </BblData>
    </Frame>
  );
}

export function SolidarityPercent() {
  return (
    <Frame>
      <BblData color="var(--babylon-solidarity)" size={12}>
        64%
      </BblData>
    </Frame>
  );
}
