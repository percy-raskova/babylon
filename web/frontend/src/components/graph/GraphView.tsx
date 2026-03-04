/**
 * Network topology graph visualization using Sigma.js + Graphology.
 *
 * Renders entities, territories, organizations, and edges as an
 * interactive force-directed graph. Nodes are color-coded by type,
 * edges by relationship type. Edge type filtering and node-click navigation.
 */

import { useEffect, useMemo, useRef, useState } from "react";
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
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  // Extract unique edge types from actual data
  const edgeTypes = useMemo(() => {
    const types = new Set<string>();
    for (const edge of snapshot.edges) {
      types.add(edge.edge_type);
    }
    return Array.from(types).sort();
  }, [snapshot.edges]);

  const graph = useMemo(() => {
    const g = buildGraph(snapshot);
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
      {/* Edge type filter */}
      <div className="absolute left-2 top-2 z-10 flex flex-wrap gap-1">
        <button
          onClick={() => setActiveFilter(null)}
          className={`rounded px-2 py-0.5 text-[9px] font-medium transition-colors ${
            activeFilter === null
              ? "bg-dark-metal text-gold"
              : "bg-void/80 text-ash hover:text-silver"
          }`}
        >
          All
        </button>
        {edgeTypes.map((type) => (
          <button
            key={type}
            onClick={() => setActiveFilter(activeFilter === type ? null : type)}
            className={`rounded px-2 py-0.5 text-[9px] font-medium transition-colors ${
              activeFilter === type
                ? "bg-dark-metal text-gold"
                : "bg-void/80 text-ash hover:text-silver"
            }`}
          >
            {type}
          </button>
        ))}
      </div>

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
        <EdgeFilter filter={activeFilter} graph={graph} />
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
    if (!loadedRef.current) {
      loadGraph(graph);
      loadedRef.current = true;
    }
  }, [graph, loadGraph]);

  useEffect(() => {
    loadedRef.current = false;
  }, [graph]);

  return null;
}

/** Applies edge type filtering via sigma nodeReducer/edgeReducer. */
function EdgeFilter({ filter }: { filter: string | null; graph: ReturnType<typeof buildGraph> }) {
  const sigma = useSigma();

  useEffect(() => {
    const graph = sigma.getGraph();
    // Build connected node set for the active filter
    const connectedNodes = new Set<string>();
    if (filter) {
      graph.forEachEdge((_edge, attrs, source, target) => {
        if (attrs.edgeType === filter) {
          connectedNodes.add(source);
          connectedNodes.add(target);
        }
      });
    }

    sigma.setSetting("nodeReducer", (node, data) => {
      if (!filter) return data;
      if (!connectedNodes.has(node)) {
        return { ...data, color: "#2a2a3a" };
      }
      return data;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      if (!filter) return data;
      const attrs = graph.getEdgeAttributes(edge);
      if (attrs.edgeType !== filter) {
        return { ...data, hidden: true };
      }
      return data;
    });

    sigma.refresh();

    return () => {
      sigma.setSetting("nodeReducer", null);
      sigma.setSetting("edgeReducer", null);
    };
  }, [filter, sigma]);

  return null;
}

/** Registers click events to sync with the UI store — pushes breadcrumbs for navigation. */
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

/** Visual legend for node and edge types. */
function GraphLegend() {
  const NODE_LEGEND = [
    { label: "Entity", color: "#6a9fdb" },
    { label: "Territory", color: "#d4a843" },
    { label: "Organization", color: "#9b59b6" },
    { label: "Institution", color: "#b0b0c0" },
  ];

  return (
    <div className="absolute bottom-2 left-2 flex gap-3 rounded bg-void/80 px-2 py-1">
      {NODE_LEGEND.map((item) => (
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
