/**
 * Inspector panel — drill-down fetch triggered by map/graph selection
 * changes, not by tick advance (spec-110 B3). Mirrors the legacy
 * `useInspector` hook's endpoint shape: `GET /api/games/{id}/{kind}/{id}/`.
 */

import { get as apiGet } from "@/api/client";

export type InspectorKind = "node" | "org" | "community" | "edge" | "hex";

export interface InspectorPanelState {
  data: Record<string, unknown> | null;
  loading: boolean;
  error: string | null;
  /** `${kind}:${id}` of the selection this data was fetched for. */
  selectionKey: string | null;
}

export interface InspectorPanel extends InspectorPanelState {
  fetchForSelection: (gameId: string, kind: InspectorKind, id: string) => Promise<void>;
  clear: () => void;
}

export function createInspectorPanel(
  updateSelf: (updater: (p: InspectorPanel) => InspectorPanel) => void,
): InspectorPanel {
  const fetchForSelection = async (
    gameId: string,
    kind: InspectorKind,
    id: string,
  ): Promise<void> => {
    const selectionKey = `${kind}:${id}`;
    updateSelf((p) => ({ ...p, loading: true, error: null, selectionKey }));
    const res = await apiGet<Record<string, unknown>>(`/api/games/${gameId}/${kind}/${id}/`);
    if (res.status === "ok") {
      updateSelf((p) =>
        p.selectionKey === selectionKey ? { ...p, data: res.data, loading: false, error: null } : p,
      );
    } else {
      updateSelf((p) =>
        p.selectionKey === selectionKey
          ? { ...p, loading: false, error: res.message ?? "Failed to load inspector data" }
          : p,
      );
    }
  };

  const clear = (): void =>
    updateSelf((p) => ({ ...p, data: null, loading: false, error: null, selectionKey: null }));

  return { data: null, loading: false, error: null, selectionKey: null, fetchForSelection, clear };
}
