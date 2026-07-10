/**
 * OutlinerRow preview — the one row shape every Outliner section list
 * uses (org / community / faction). A bare row floating alone on a card
 * isn't how this component is ever seen in the app, so each cell composes
 * a short realistic row list the way `Outliner.tsx` actually renders one
 * section's children — the row-list container styling (`flex flex-col
 * gap-0.5 py-1.5`) is lifted verbatim from `OutlinerSection`'s content
 * wrapper so these leaves render true to their parent context.
 *
 * Pure props, no store — no cardMode override needed (nothing to lie
 * about on a combined card).
 *
 * Width is an inline `style`, not a Tailwind arbitrary-value class:
 * Tailwind v4's automatic content scan is rooted at
 * `src/frontend/src/index.css` and never walks `.design-sync/previews/`,
 * so an arbitrary class unique to a preview file (`w-[280px]`) silently
 * compiles to nothing — see `.design-sync/learnings/shell.md`.
 */
import { OutlinerRow } from "babylon-cockpit";

function RowList({ children }: { children?: unknown }) {
  return (
    <div style={{ width: 280 }} className="bg-void p-2">
      <div className="flex flex-col gap-0.5 py-1.5">{children as never}</div>
    </div>
  );
}

export function OrganizationRows() {
  return (
    <RowList>
      <OutlinerRow label="UAW Local 600" sublabel="civil_society_org" selected onClick={() => {}} />
      <OutlinerRow label="Detroit PD" sublabel="state_apparatus" onClick={() => {}} />
      <OutlinerRow label="Renaissance Capital Partners" sublabel="business" onClick={() => {}} />
    </RowList>
  );
}

export function CommunityRows() {
  return (
    <RowList>
      <OutlinerRow label="proletariat" sublabel="340 members" onClick={() => {}} />
      <OutlinerRow label="petite_bourgeoisie" sublabel="58 members" onClick={() => {}} />
    </RowList>
  );
}

export function NoSublabelRows() {
  return (
    <RowList>
      <OutlinerRow label="FAC_DECOLONIAL" onClick={() => {}} />
      <OutlinerRow label="FAC_LOYALIST" selected onClick={() => {}} />
    </RowList>
  );
}
