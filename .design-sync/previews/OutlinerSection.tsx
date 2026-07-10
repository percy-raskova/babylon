/**
 * OutlinerSection preview — the collapsible header + row-list wrapper
 * every Outliner section shares. Composed with real `OutlinerRow`
 * children (it is never used standalone in the real app) — mirrors
 * `Outliner.tsx`'s three sections, including its local `EmptyRow`
 * empty-copy pattern (that helper isn't exported from `Outliner.tsx`, so
 * the empty cell reproduces its markup inline: `text-[10px] italic
 * text-shroud`).
 *
 * `defaultOpen` is a plain JSX prop (not store state), so the
 * open/collapsed axis is statically renderable without any interaction.
 *
 * Pure props, no store — no cardMode override needed.
 *
 * Width is an inline `style`, not a Tailwind arbitrary-value class — see
 * `.design-sync/learnings/shell.md` (Tailwind's content scan never walks
 * `.design-sync/previews/`, so unique arbitrary classes there compile away).
 */
import { OutlinerSection, OutlinerRow } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div style={{ width: 280 }} className="bg-void p-2">{children as never}</div>;
}

export function OrganizationsOpen() {
  return (
    <Frame>
      <OutlinerSection title="Organizations" count={3}>
        <OutlinerRow label="UAW Local 600" sublabel="civil_society_org" selected onClick={() => {}} />
        <OutlinerRow label="Detroit PD" sublabel="state_apparatus" onClick={() => {}} />
        <OutlinerRow label="Renaissance Capital Partners" sublabel="business" onClick={() => {}} />
      </OutlinerSection>
    </Frame>
  );
}

export function FactionsCollapsed() {
  return (
    <Frame>
      <OutlinerSection title="Factions" count={2} defaultOpen={false}>
        <OutlinerRow label="FAC_DECOLONIAL" sublabel="abolish" onClick={() => {}} />
        <OutlinerRow label="FAC_LOYALIST" sublabel="uphold" onClick={() => {}} />
      </OutlinerSection>
    </Frame>
  );
}

export function CommunitiesEmpty() {
  return (
    <Frame>
      <OutlinerSection title="Communities" count={0}>
        <p className="px-2 py-1 text-[10px] italic text-shroud">No communities formed yet.</p>
      </OutlinerSection>
    </Frame>
  );
}
