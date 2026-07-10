/**
 * ObjectivesTracker preview — the Right Dock's third tab, Vic3-style
 * objectives mapped to the 5 endgame conditions. Store-driven via the
 * `useObjectives` hook, which fetches on mount — same inert-fetch-override
 * technique as TimeseriesChart (see that file's docstring and learnings).
 *
 * Cells set different store states, so the combined card lies (singleton
 * store) — needs cfg.overrides.ObjectivesTracker = {cardMode: "single",
 * primaryStory: "Populated"} (see learnings).
 */
import { ObjectivesTracker, useStore } from "babylon-cockpit";

async function noopFetch(): Promise<void> {}
function noopSetMounted(): void {}

function seedObjectives(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      objectives: {
        ...s.panels.objectives,
        data: null,
        loading: false,
        error: null,
        fetch: noopFetch,
        setMounted: noopSetMounted,
        ...patch,
      },
    },
  }));
}

const OBJECTIVES = [
  {
    id: "obj-dual-power",
    title: "Establish Dual Power in Wayne County",
    description: "Push P(S|R) past P(S|A) county-wide via SOLIDARITY edge growth among the proletariat.",
    progress: 0.64,
    status: "active",
    category: "revolution",
  },
  {
    id: "obj-imperial-rent-collapse",
    title: "Collapse the Imperial Rent Flow",
    description: "Drive Imperial Rent Φ toward zero by severing TRIBUTE edges out of the core.",
    progress: 0.22,
    status: "active",
    category: "collapse",
  },
  {
    id: "obj-fascist-consolidation-averted",
    title: "Prevent Fascist Consolidation",
    description: "Keep the reserve army's fascist consciousness pole below the bifurcation threshold.",
    progress: 1.0,
    status: "complete",
    category: "fascist",
  },
];

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[320px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void" style={{ width: 320 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  seedObjectives({ data: { tick: 104, objectives: OBJECTIVES } });
  return (
    <Frame>
      <ObjectivesTracker gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoadingState() {
  seedObjectives({ loading: true });
  return (
    <Frame>
      <ObjectivesTracker gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoudEmpty() {
  seedObjectives({ data: { tick: 104, objectives: [] } });
  return (
    <Frame>
      <ObjectivesTracker gameId="g-wayne-county-104" />
    </Frame>
  );
}

export function LoudFailure() {
  seedObjectives({ error: "Objectives unavailable: HTTP 500" });
  return (
    <Frame>
      <ObjectivesTracker gameId="g-wayne-county-104" />
    </Frame>
  );
}
