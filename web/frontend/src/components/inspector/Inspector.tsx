/**
 * Inspector — routes to NodeInspector or HexInspector based on the
 * current UI store selection. Falls back to the OrgDashboard list
 * when nothing is selected.
 */

import { useUIStore } from "@/stores/uiStore";
import { NodeInspector } from "@/components/inspector/NodeInspector";
import { HexInspector } from "@/components/inspector/HexInspector";
import { OrgDashboard } from "@/components/OrgDashboard";
import type { GameSnapshot } from "@/types/game";

interface InspectorProps {
  snapshot: GameSnapshot;
}

export function Inspector({ snapshot }: InspectorProps) {
  const selectedNodeId = useUIStore((s) => s.selectedNodeId);
  const selectedHexId = useUIStore((s) => s.selectedHexId);
  const clearNode = useUIStore((s) => s.setSelectedNode);
  const clearHex = useUIStore((s) => s.setSelectedHex);

  // Node selection takes priority over hex selection
  if (selectedNodeId) {
    return (
      <div className="flex h-full flex-col overflow-auto">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gold">Inspector</h3>
          <button
            onClick={() => clearNode(null)}
            className="rounded px-2 py-0.5 text-[10px] text-ash hover:bg-soot hover:text-silver"
          >
            Clear
          </button>
        </div>
        <NodeInspector snapshot={snapshot} nodeId={selectedNodeId} />
      </div>
    );
  }

  if (selectedHexId) {
    return (
      <div className="flex h-full flex-col overflow-auto">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gold">Inspector</h3>
          <button
            onClick={() => clearHex(null)}
            className="rounded px-2 py-0.5 text-[10px] text-ash hover:bg-soot hover:text-silver"
          >
            Clear
          </button>
        </div>
        <HexInspector snapshot={snapshot} hexId={selectedHexId} />
      </div>
    );
  }

  // Default: show org list (as before)
  return <OrgDashboard snapshot={snapshot} />;
}
