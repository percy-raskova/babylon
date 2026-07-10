/**
 * InspectorPanel preview — Right Dock tab 2, selected node/org/hex detail.
 * Store-driven (`map.selection` + `panels.inspector`) but does NOT fetch on
 * mount itself — the real fetch only fires through `mapSlice.setSelection`,
 * which this preview deliberately never calls (it patches `map.selection`
 * directly instead), so no network race exists here. Each cell seeds the
 * store inside its own wrapper, always spreading the existing slices.
 *
 * Cells set different store states, so the combined card lies (singleton
 * store) — needs cfg.overrides.InspectorPanel = {cardMode: "single",
 * primaryStory: "OrgWithConsciousness"} (see learnings).
 */
import { InspectorPanel, useStore } from "babylon-cockpit";

function seedInspector(selection: Record<string, unknown> | null, patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    map: { ...s.map, selection },
    panels: {
      ...s.panels,
      inspector: { ...s.panels.inspector, data: null, loading: false, error: null, ...patch },
    },
  }));
}

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[320px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void" style={{ width: 320 }}>
      {children as never}
    </div>
  );
}

export function EmptySelection() {
  seedInspector(null, {});
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}

export function OrgWithConsciousness() {
  seedInspector(
    { kind: "org", id: "org-uaw-local-600" },
    {
      data: {
        kind: "org",
        id: "org-uaw-local-600",
        class_character: "proletarian",
        budget: 84.2,
        cohesion: 0.58,
        heat: 0.34,
        consciousness: { liberal: 0.31, fascist: 0.27, revolutionary: 0.42 },
      },
    },
  );
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}

export function OrgConsciousnessNoData() {
  seedInspector(
    { kind: "org", id: "org-liberal-ngo-14" },
    {
      data: {
        kind: "org",
        id: "org-liberal-ngo-14",
        class_character: "petit_bourgeois",
        budget: 12.6,
        cohesion: 0.44,
        heat: 0.09,
        consciousness: null,
      },
    },
  );
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}

export function TerritoryHex() {
  seedInspector(
    { kind: "hex", id: "territory-detroit-downtown" },
    {
      data: {
        kind: "hex",
        id: "territory-detroit-downtown",
        habitability: 0.24,
        biocapacity: 0.18,
        heat: 0.71,
        rent_level: 0.62,
        population: 84213,
      },
    },
  );
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}

export function LoadingState() {
  seedInspector({ kind: "org", id: "org-uaw-local-600" }, { loading: true });
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}

export function LoudError() {
  seedInspector({ kind: "node", id: "node-unknown-88" }, { error: "Node not found" });
  return (
    <Frame>
      <InspectorPanel />
    </Frame>
  );
}
