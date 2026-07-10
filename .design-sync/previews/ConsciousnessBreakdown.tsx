/**
 * ConsciousnessBreakdown preview — org ternary consciousness distribution,
 * null-honesty per Constitution III.11 (`consciousness: null` renders "no
 * data", never a fabricated thirds split). Pure props, no store.
 */
import { ConsciousnessBreakdown } from "babylon-cockpit";

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[260px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void p-3" style={{ width: 260 }}>
      {children as never}
    </div>
  );
}

export function RevolutionaryLeaning() {
  return (
    <Frame>
      <ConsciousnessBreakdown consciousness={{ liberal: 0.31, fascist: 0.27, revolutionary: 0.42 }} />
    </Frame>
  );
}

export function FascistDrift() {
  return (
    <Frame>
      <ConsciousnessBreakdown consciousness={{ liberal: 0.22, fascist: 0.51, revolutionary: 0.27 }} />
    </Frame>
  );
}

export function NoData() {
  return (
    <Frame>
      <ConsciousnessBreakdown consciousness={null} />
    </Frame>
  );
}
