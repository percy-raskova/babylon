/**
 * VerbGrid preview — the flat 9-verb grid (Constitution Article V: no
 * invented tabs/groupings). VERBS/DISABLED_VERBS are internal to the
 * component (not props), so the grid's 9 buttons and the 3 disabled ones
 * (investigate/move/negotiate — no engine handler yet, Spec 061 FR-025)
 * are identical across cells; the only variant axis is which verb (if
 * any) is highlighted as the active selection.
 */
import { VerbGrid } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[380px] bg-void p-3">{children as never}</div>;
}

export function Unselected() {
  return (
    <Frame>
      <VerbGrid selectedVerb={null} onSelect={() => {}} />
    </Frame>
  );
}

export function AttackSelected() {
  return (
    <Frame>
      <VerbGrid selectedVerb="attack" onSelect={() => {}} />
    </Frame>
  );
}
