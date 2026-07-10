/**
 * BblLabel preview — uppercase micro-label (category labels, section
 * headers, axis labels). Pure props, no store.
 */
import { BblLabel } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="flex items-center gap-4 bg-void p-4">{children as never}</div>;
}

export function DefaultSectionHeader() {
  return (
    <Frame>
      <BblLabel>Imperial Rent</BblLabel>
    </Frame>
  );
}

export function AccentColored() {
  return (
    <Frame>
      <BblLabel color="var(--babylon-solidarity)">Solidarity</BblLabel>
    </Frame>
  );
}

export function AxisLabel() {
  return (
    <Frame>
      <BblLabel color="var(--babylon-ash)">Tick</BblLabel>
    </Frame>
  );
}
