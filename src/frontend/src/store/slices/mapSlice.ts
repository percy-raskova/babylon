/**
 * Map slice — the unified `Lens` (spec-110 B2) plus selection and viewport
 * (spec-110 B3). Distinct from `panels.map`: this slice is view *controls*
 * (what the map should show and what's selected on it); `panels.map` is
 * the fetched GeoJSON *data* for the current framing/tick.
 *
 * Selection changes fan out an inspector fetch (`panels.inspector`) —
 * the map/graph/table views all write through `setSelection` so the
 * inspector panel stays in sync with whatever's clicked anywhere in the
 * cockpit, without each view owning its own inspector fetch.
 */

import type { StateCreator } from "zustand";
import { DEFAULT_LENS, type Lens } from "@/lib/lens";
import type { AdminLevel } from "@/types/game";
import type { RootState } from "../types";
import type { InspectorKind } from "./panels/inspectorPanel";

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
    framing: "hex",
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
      const gameId = get().session.activeGameId;
      if (selection && gameId) {
        get().panels.inspector.fetchForSelection(gameId, selection.kind, selection.id);
      } else {
        get().panels.inspector.clear();
      }
    },
  },
});
