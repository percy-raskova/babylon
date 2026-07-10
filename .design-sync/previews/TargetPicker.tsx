/**
 * TargetPicker preview — pure presentational (targets/loading/error/
 * selectedId all arrive as props; no store, no fetch), so every branch is
 * directly seedable. Sweeps the data-availability axis (loading / loud
 * failure / honest-empty / populated) plus grouped-vs-ungrouped target
 * lists — grouping mirrors real VerbConfig.parseTargets output (Aid's
 * Communities/Organizations split vs. Educate's flat labeled list).
 */
import { TargetPicker } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[380px] bg-void p-3">{children as never}</div>;
}

export function Loading() {
  return (
    <Frame>
      <TargetPicker targets={[]} loading={true} error={null} selectedId={null} onSelect={() => {}} />
    </Frame>
  );
}

export function LoudFailure() {
  return (
    <Frame>
      <TargetPicker
        targets={[]}
        loading={false}
        error="Failed to fetch action targets"
        selectedId={null}
        onSelect={() => {}}
      />
    </Frame>
  );
}

export function HonestEmpty() {
  return (
    <Frame>
      <TargetPicker targets={[]} loading={false} error={null} selectedId={null} onSelect={() => {}} />
    </Frame>
  );
}

const AID_STYLE_TARGETS = [
  { id: "comm-hamtramck-tenants", label: "Hamtramck Tenants Assembly", group: "Communities" },
  { id: "comm-48210-block-club", label: "48210 Block Club", group: "Communities" },
  { id: "org-uaw-local-600", label: "UAW Local 600", group: "Organizations" },
  { id: "org-detroit-dsa", label: "Detroit DSA", group: "Organizations" },
];

export function GroupedWithSelection() {
  return (
    <Frame>
      <TargetPicker
        targets={AID_STYLE_TARGETS}
        loading={false}
        error={null}
        selectedId="org-uaw-local-600"
        onSelect={() => {}}
      />
    </Frame>
  );
}

const EDUCATE_STYLE_TARGETS = [
  { id: "comm-hamtramck-1", label: "Hamtramck (labor — Credibility: 0.62)" },
  { id: "comm-river-rouge-2", label: "River Rouge (labor — Credibility: 0.48)" },
  { id: "comm-downtown-3", label: "Downtown (civic — Credibility: 0.31)" },
];

export function UngroupedList() {
  return (
    <Frame>
      <TargetPicker
        targets={EDUCATE_STYLE_TARGETS}
        loading={false}
        error={null}
        selectedId={null}
        onSelect={() => {}}
      />
    </Frame>
  );
}
