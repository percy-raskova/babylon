/**
 * NetworkTakeover — the Network takeover (AW4-R2, audit Wave 4 "Topology &
 * the Gramscian Wire"): a sigma.js node-link view of the org/institution/
 * territory topology graph, one-shot-fetched on open via `useOrgNetwork`
 * (mirrors `useWire`/`useContradiction`'s mount/fetch idiom — the takeover
 * owns its own fetch, `TakeoverOverlay` only owns the escape/close chrome).
 *
 * Header bar carries the node/edge counts, the percolation-ratio HUD chip
 * (scoped here per the audit brief, not global `TopBar` chrome), and an
 * honest legend — both the legend and the graph itself only ever encode
 * node types / edge modes actually present in the real payload
 * (`presentNodeTypes`/`presentEdgeModes`), never a fabricated universal
 * roster. Constitution III.11: an empty network renders an honest empty
 * state, never fabricated nodes.
 */

import { useMemo } from "react";
import { useOrgNetwork } from "@/hooks/useOrgNetwork";
import { NetworkGraphCanvas } from "./NetworkGraphCanvas";
import {
  buildOrgNetworkGraph,
  presentNodeTypes,
  presentEdgeModes,
  NODE_TYPE_COLOR,
  SOLIDARITY_EDGE_COLOR,
  DEFAULT_EDGE_COLOR,
} from "@/lib/network/buildOrgNetworkGraph";
import type { OrgNetworkNode } from "@/types/game";

interface Props {
  gameId: string;
}

/** Percolation HUD chip — mirrors `StatChip`'s visual convention (border-2
 *  ksbc-muted-1 plate, uppercase label over a mono value) but is a small
 *  local element rather than a reuse of `StatChip` itself: `percolation_ratio`
 *  has no `METRIC_PROVENANCE` entry (verified against
 *  `web/game/provenance.py`), so it stays non-clickable like TopBar's own
 *  "Pop" chip, and the null glyph is the em-dash `HexTooltip.tsx` already
 *  uses for an honest missing value, not `StatChip`'s own "no data" text. */
function PercolationChip({ value }: { value: number | null }): React.JSX.Element {
  const hasData = value !== null;
  return (
    <div
      className="flex items-center gap-1.5 border-2 border-ksbc-muted-1 bg-plate px-2.5 py-1"
      data-testid="stat-percolation"
    >
      <span className="text-[9px] uppercase tracking-widest text-ksbc-muted-2">Percolation</span>
      <span
        className={`font-mono text-[11px] font-semibold ${
          hasData ? "text-solidarity" : "italic text-ksbc-muted-1"
        }`}
      >
        {hasData ? value.toFixed(3) : "—"}
      </span>
    </div>
  );
}

/** One legend swatch — a colored dot for a node type or a colored bar for
 *  an edge mode, labeled with the raw wire value (never a fabricated
 *  friendly name — matches `mode`'s own "mechanical EdgeType value,
 *  lowercase" convention from `engine_bridge.py::_build_org_network`). */
function NodeTypeSwatch({ type }: { type: OrgNetworkNode["type"] }): React.JSX.Element {
  return (
    <span className="flex items-center gap-1">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ background: NODE_TYPE_COLOR[type] }}
      />
      <span className="uppercase tracking-widest text-ksbc-muted-2">{type}</span>
    </span>
  );
}

function EdgeModeSwatch({ mode }: { mode: string }): React.JSX.Element {
  const color = mode === "solidarity" ? SOLIDARITY_EDGE_COLOR : DEFAULT_EDGE_COLOR;
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block h-0.5 w-4" style={{ background: color }} />
      <span className="uppercase tracking-widest text-ksbc-muted-2">{mode}</span>
    </span>
  );
}

function Legend({
  nodeTypes,
  edgeModes,
}: {
  nodeTypes: OrgNetworkNode["type"][];
  edgeModes: string[];
}): React.JSX.Element | null {
  if (nodeTypes.length === 0 && edgeModes.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 text-[10px]" data-testid="network-legend">
      {nodeTypes.map((type) => (
        <NodeTypeSwatch key={type} type={type} />
      ))}
      {edgeModes.map((mode) => (
        <EdgeModeSwatch key={mode} mode={mode} />
      ))}
    </div>
  );
}

export function NetworkTakeover({ gameId }: Props): React.JSX.Element {
  const { data, loading, error } = useOrgNetwork(gameId);

  const graph = useMemo(() => buildOrgNetworkGraph(data), [data]);
  const nodeTypes = useMemo(() => presentNodeTypes(data), [data]);
  const edgeModes = useMemo(() => presentEdgeModes(data), [data]);
  const isEmpty = data.nodes.length === 0;

  return (
    <div className="flex h-full w-full flex-col" data-testid="network-takeover">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ksbc-muted-1 px-3 py-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] uppercase tracking-widest text-ksbc-muted-2">
            {data.nodes.length} nodes · {data.edges.length} edges
          </span>
          <PercolationChip value={data.percolation_ratio} />
        </div>
        <Legend nodeTypes={nodeTypes} edgeModes={edgeModes} />
      </header>

      <div className="min-h-0 flex-1">
        {loading && isEmpty && <p className="p-3 text-[11px] text-ash">Loading network…</p>}
        {error && (
          <p role="alert" className="p-3 text-[11px] text-laser">
            {error}
          </p>
        )}
        {!loading && !error && isEmpty && (
          <p className="p-3 text-[11px] italic text-shroud" data-testid="network-empty">
            No organizational network recorded in this graph yet.
          </p>
        )}
        {!isEmpty && <NetworkGraphCanvas graph={graph} />}
      </div>
    </div>
  );
}
