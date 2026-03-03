/**
 * Network topology graph visualization using Sigma.js + Graphology.
 *
 * Renders entities, territories, organizations, and edges as an
 * interactive force-directed graph. Nodes are color-coded by type,
 * edges by relationship type.
 */

import { useEffect, useMemo, useRef } from "react";
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from "@react-sigma/core";
import "@react-sigma/core/lib/style.css";
import forceAtlas2 from "graphology-layout-forceatlas2";
import type { GameSnapshot } from "@/types/game";
import { buildGraph } from "@/utils/graphBuilder";
import { useUIStore } from "@/stores/uiStore";

interface GraphViewProps {
  snapshot: GameSnapshot;
}

/** Max iterations for the initial ForceAtlas2 layout pass. */
const FA2_ITERATIONS = 50;

export function GraphView({ snapshot }: GraphViewProps) {
  const graph = useMemo(() => {
    const g = buildGraph(snapshot);
    // Run synchronous ForceAtlas2 layout
    if (g.order > 0) {
      forceAtlas2.assign(g, {
        iterations: FA2_ITERATIONS,
        settings: {
          gravity: 1,
          scalingRatio: 10,
          barnesHutOptimize: g.order > 100,
        },
      });
    }
    return g;
  }, [snapshot]);

  return (
    <div className="relative h-full w-full">
      <SigmaContainer
        graph={graph}
        style={{ height: "100%", width: "100%", background: "#08081a" }}
        settings={{
          defaultNodeColor: "#6a9fdb",
          defaultEdgeColor: "#3a3a4a",
          labelColor: { color: "#b0b0c0" },
          labelFont: "Inter, sans-serif",
          labelSize: 10,
          renderEdgeLabels: false,
          enableEdgeEvents: false,
        }}
      >
        <GraphLoader graph={graph} />
        <GraphEvents />
        <GraphLegend />
      </SigmaContainer>
    </div>
  );
}

/** Loads/reloads the graph when snapshot changes. */
function GraphLoader({ graph }: { graph: ReturnType<typeof buildGraph> }) {
  const loadGraph = useLoadGraph();
  const loadedRef = useRef(false);

  useEffect(() => {
    // Only reload if graph instance changes
    if (!loadedRef.current) {
      loadGraph(graph);
      loadedRef.current = true;
    }
  }, [graph, loadGraph]);

  // Reset on graph change
  useEffect(() => {
    loadedRef.current = false;
  }, [graph]);

  return null;
}

/** Registers click events to sync with the UI store. */
function GraphEvents() {
  const sigma = useSigma();
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);
  const registerEvents = useRegisterEvents();

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        setSelectedNode(event.node);
      },
      clickStage: () => {
        setSelectedNode(null);
      },
    });
  }, [registerEvents, setSelectedNode, sigma]);

  return null;
}

/** Visual legend for node types. */
function GraphLegend() {
  const LEGEND_ITEMS = [
    { label: "Entity", color: "#6a9fdb" },
    { label: "Territory", color: "#d4a843" },
    { label: "Organization", color: "#9b59b6" },
    { label: "Institution", color: "#b0b0c0" },
  ];

  return (
    <div className="absolute bottom-2 left-2 flex gap-3 rounded bg-void/80 px-2 py-1">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-1">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-[10px] text-ash">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
