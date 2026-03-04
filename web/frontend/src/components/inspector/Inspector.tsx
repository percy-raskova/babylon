/**
 * Inspector — routes to NodeInspector or HexInspector based on the
 * current UI store selection. Falls back to the OrgDashboard list
 * when nothing is selected. Renders Breadcrumbs for drill-down navigation.
 */

import { useEffect, useRef } from "react";
import { useUIStore } from "@/stores/uiStore";
import { NodeInspector } from "@/components/inspector/NodeInspector";
import { HexInspector } from "@/components/inspector/HexInspector";
import { Breadcrumbs } from "@/components/inspector/Breadcrumbs";
import { OrgDashboard } from "@/components/OrgDashboard";
import type { GameSnapshot } from "@/types/game";

interface InspectorProps {
  snapshot: GameSnapshot;
}

export function Inspector({ snapshot }: InspectorProps) {
  const selectedNodeId = useUIStore((s) => s.selectedNodeId);
  const selectedHexId = useUIStore((s) => s.selectedHexId);
  const pushBreadcrumb = useUIStore((s) => s.pushBreadcrumb);
  const activeLens = useUIStore((s) => s.activeLens);
  const prevHexRef = useRef<string | null>(null);
  const prevNodeRef = useRef<string | null>(null);

  // Push breadcrumbs when selection changes
  useEffect(() => {
    if (selectedHexId && selectedHexId !== prevHexRef.current) {
      const territory = snapshot.territories.find((t) => t.id === selectedHexId);
      if (territory) {
        pushBreadcrumb({
          entityType: "territory",
          entityId: selectedHexId,
          displayName: territory.name,
          lensId: activeLens,
        });
      }
    }
    prevHexRef.current = selectedHexId;
  }, [selectedHexId, snapshot.territories, pushBreadcrumb, activeLens]);

  useEffect(() => {
    if (selectedNodeId && selectedNodeId !== prevNodeRef.current) {
      const entity = snapshot.entities.find((e) => e.id === selectedNodeId);
      const org = snapshot.organizations.find((o) => o.id === selectedNodeId);
      const inst = snapshot.institutions.find((i) => i.id === selectedNodeId);
      const found = entity ?? org ?? inst;
      if (found) {
        let entityType: "entity" | "organization" | "institution" = "institution";
        if (entity) entityType = "entity";
        else if (org) entityType = "organization";
        pushBreadcrumb({
          entityType,
          entityId: selectedNodeId,
          displayName: found.name,
          lensId: activeLens,
        });
      }
    }
    prevNodeRef.current = selectedNodeId;
  }, [
    selectedNodeId,
    snapshot.entities,
    snapshot.organizations,
    snapshot.institutions,
    pushBreadcrumb,
    activeLens,
  ]);

  const hasSelection = selectedNodeId || selectedHexId;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <Breadcrumbs />
      {!hasSelection && <OrgDashboard snapshot={snapshot} />}
      {selectedNodeId && (
        <div className="flex-1 overflow-auto">
          <NodeInspector snapshot={snapshot} nodeId={selectedNodeId} />
        </div>
      )}
      {!selectedNodeId && selectedHexId && (
        <div className="flex-1 overflow-auto">
          <HexInspector snapshot={snapshot} hexId={selectedHexId} />
        </div>
      )}
    </div>
  );
}
