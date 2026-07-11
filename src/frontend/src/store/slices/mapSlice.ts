/**
 * Map slice — the unified `Lens` (spec-110 B2) plus selection and viewport
 * (spec-110 B3). Distinct from `panels.map`: this slice is view *controls*
 * (what the map should show and what's selected on it); `panels.map` is
 * the fetched GeoJSON *data* for the current framing/tick.
 *
 * Selection changes fan out into the InspectionStack (spec-113 Lane C) —
 * the map/graph/table views all write through `setSelection` so the
 * inspection stack stays in sync with whatever's clicked anywhere in the
 * cockpit, without each view owning its own inspector fetch. This
 * replaces the B3-era direct fan-out to the (now-deleted)
 * `panels.inspector`/`InspectorPanel` — the `Selection` shape and
 * `setSelection` signature are unchanged, only where the fetch happens.
 */

import type { StateCreator } from "zustand";
import { DEFAULT_LENS, type Lens } from "@/lib/lens";
import type { AdminLevel } from "@/types/game";
import type { RootState } from "../types";

/**
 * The five concrete entity kinds a map/graph/table click can select
 * (relocated from the deleted `panels/inspectorPanel.ts` — spec-113 Lane
 * C absorbs the Inspector into `inspect/*`; `panels/index.ts` re-exports
 * this name from here so `store/index.ts`'s existing
 * `export type { ... InspectorKind } from "./slices/panels"` line needs
 * no edit). Deliberately narrower than `InspectionRefKind`
 * (`types/inspection.ts`), which also covers `"metric"`/`"formula"` —
 * only concrete entities are ever map-clickable.
 */
export type InspectorKind = "node" | "org" | "community" | "edge" | "hex";

export interface Selection {
  kind: InspectorKind;
  id: string;
}

export interface MapSlice {
  map: {
    lens: Lens;
    /** Admin-level spatial aggregation for `panels.map`'s `/map/?zoom=` fetch. */
    framing: AdminLevel;
    viewportBbox: [number, number, number, number] | null;
    selection: Selection | null;
    /** Selected faction id for the "faction" lens (Outliner + MapModeSelector). */
    factionFilter: string | null;

    setLens: (lens: Lens) => void;
    setFraming: (level: AdminLevel) => void;
    setViewportBbox: (bbox: [number, number, number, number] | null) => void;
    /** Set (or clear, with `null`) the active selection; fans out an inspector fetch. */
    setSelection: (selection: Selection | null) => void;
    setFactionFilter: (factionId: string | null) => void;
  };
}

export const createMapSlice: StateCreator<RootState, [], [], MapSlice> = (set, get) => ({
  map: {
    lens: DEFAULT_LENS,
    // "county" is the default framing (spec-113 Lane C, on Lane B's
    // behalf — DESIGN_BIBLE.md §9.2/Carto addendum: real county
    // cartography is now the visible map, hexes are the deep-zoom tile
    // register). Was "hex" pre-Living-Map (spec-112 C5).
    framing: "county",
    viewportBbox: null,
    selection: null,
    factionFilter: null,

    setLens: (lens) => set((s) => ({ map: { ...s.map, lens } })),

    // A framing change means the `/map/?zoom=` fetch's response shape
    // changes (hex vs. aggregated-region features) — refetch, mirroring
    // setSelection's fan-out below (fire-and-forget; no active game means
    // no fetch, but framing still updates).
    setFraming: (level) => {
      set((s) => ({ map: { ...s.map, framing: level } }));
      const gameId = get().session.activeGameId;
      if (gameId) {
        get().panels.map.fetch(gameId);
      }
    },
    setViewportBbox: (bbox) => set((s) => ({ map: { ...s.map, viewportBbox: bbox } })),
    setFactionFilter: (factionId) => set((s) => ({ map: { ...s.map, factionFilter: factionId } })),

    setSelection: (selection) => {
      set((s) => ({ map: { ...s.map, selection } }));
      // Reroute (spec-113 Lane C): always reset the InspectionStack to a
      // single fresh frame for the new selection — clear() then push()
      // rather than a bespoke "replace the current frame" method, so a
      // map click always starts a new drill-down at the root, matching
      // the old inspector's "one entity at a time" behavior. `inspect`
      // itself (not `panels.inspector`) now owns fetch/loading/error.
      get().inspect.clear();
      if (selection) {
        get().inspect.push({ kind: selection.kind, id: selection.id });
      }
    },
  },
});
