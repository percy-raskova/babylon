/**
 * RightDock preview — the three-tab dock (Actions / Inspector /
 * Objectives). Store-driven: `ui.rightDockTab` picks the tab;
 * `ActionComposer` reads `world.snapshot.organizations` (player-controlled
 * only) + `actions.*`; `InspectorPanel` reads `map.selection` +
 * `panels.inspector`; `ObjectivesTracker`'s `useObjectives` hook is a thin
 * adapter over `panels.objectives` (`src/hooks/useObjectives.ts`) — same
 * seedable panel shape as any other docked panel.
 *
 * Two gotchas worked around here (both written up in
 * .design-sync/learnings/shell.md):
 *  1. Width is an inline `style`, not a Tailwind arbitrary-value class —
 *     Tailwind's content scan never walks `.design-sync/previews/`, so a
 *     unique `w-[320px]` class there compiles to nothing. `<aside>`'s own
 *     content is list-driven (no chart/canvas), so it renders fine at its
 *     natural content height without a forced-height wrapper.
 *  2. `objectives.fetch` is overridden to a no-op — `useObjectives`'s
 *     mount effect always fires `fetchObjectives(gameId)` against the
 *     capture harness's static file server (a real HTTP 404), and
 *     `ObjectivesTracker` renders "Error: {error}" whenever `error` is
 *     set REGARDLESS of whether `data` is also populated (it's not an
 *     early-return, both render). Without this override the populated
 *     cell shows a spurious "Error: HTTP 404" banner above real objectives.
 *
 * Card shows the primary story only (needs cfg.overrides.RightDock =
 * {cardMode:"single", primaryStory:"ActionsPopulated"}).
 */
import { RightDock, useStore } from "babylon-cockpit";

const PLAYER_ORG = {
  id: "org-uaw-local-600",
  name: "UAW Local 600",
  short_name: "UAW Local 600",
  player_controlled: true,
  org_type: "civil_society_org",
  class_character: "proletarian",
  cohesion: 0.68,
  cadre_level: 0.42,
  budget: 82.0,
  heat: 0.35,
  territory_ids: ["territory-detroit-mi"],
  hyperedge_memberships: ["hx-new-afrikan"],
  consciousness: { liberal: 0.12, fascist: 0.03, revolutionary: 0.85 },
  ooda: { observe: 0.6, orient: 0.55, decide: 0.7, act: 0.75, cycle_ticks: 1 },
};

function Frame({ children }: { children?: unknown }) {
  return (
    <div style={{ width: 320 }} className="bg-void p-2">
      {children as never}
    </div>
  );
}

export function ActionsPopulated() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, organizations: [PLAYER_ORG], events: [] } },
    ui: { ...s.ui, rightDockTab: "actions" },
    actions: {
      ...s.actions,
      pending: [
        {
          id: "pending-1",
          verb: "educate",
          orgId: "org-uaw-local-600",
          targetId: null,
          submittedAtTick: 104,
        },
      ],
      submitting: false,
      error: null,
    },
  }));
  return (
    <Frame>
      <RightDock gameId="wayne-county-001" />
    </Frame>
  );
}

export function InspectorSelected() {
  useStore.setState((s: any) => ({
    world: { ...s.world, snapshot: { tick: 104, organizations: [PLAYER_ORG], events: [] } },
    ui: { ...s.ui, rightDockTab: "inspector" },
    map: { ...s.map, selection: { kind: "org", id: "org-uaw-local-600" } },
    panels: {
      ...s.panels,
      inspector: {
        ...s.panels.inspector,
        data: {
          class_character: "proletarian",
          budget: 82.0,
          cohesion: 0.68,
          heat: 0.35,
          consciousness: { liberal: 0.12, fascist: 0.03, revolutionary: 0.85 },
        },
        loading: false,
        error: null,
        selectionKey: "org:org-uaw-local-600",
      },
    },
  }));
  return (
    <Frame>
      <RightDock gameId="wayne-county-001" />
    </Frame>
  );
}

export function InspectorEmpty() {
  useStore.setState((s: any) => ({
    ui: { ...s.ui, rightDockTab: "inspector" },
    map: { ...s.map, selection: null },
    panels: { ...s.panels, inspector: { ...s.panels.inspector, data: null, selectionKey: null } },
  }));
  return (
    <Frame>
      <RightDock gameId="wayne-county-001" />
    </Frame>
  );
}

export function ObjectivesPopulated() {
  useStore.setState((s: any) => ({
    ui: { ...s.ui, rightDockTab: "objectives" },
    panels: {
      ...s.panels,
      objectives: {
        ...s.panels.objectives,
        loading: false,
        error: null,
        fetch: async () => {},
        data: {
          tick: 104,
          objectives: [
            {
              id: "revolution",
              title: "Revolutionary Victory",
              description:
                "Build mass class consciousness and solidarity edges to overthrow the empire.",
              progress: 0.42,
              status: "active",
              category: "revolution",
            },
            {
              id: "ecological-collapse",
              title: "Avert Ecological Collapse",
              description: "Keep metabolic overshoot below the biocapacity ceiling.",
              progress: 0.71,
              status: "active",
              category: "collapse",
            },
            {
              id: "fascist-consolidation",
              title: "Fascist Consolidation Averted",
              description: "Prevent the reserve army from routing into organized fascism.",
              progress: 1.0,
              status: "complete",
              category: "fascist",
            },
          ],
        },
      },
    },
  }));
  return (
    <Frame>
      <RightDock gameId="wayne-county-001" />
    </Frame>
  );
}
