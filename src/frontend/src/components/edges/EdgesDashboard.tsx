/**
 * EdgesDashboard — the `/edges/` BottomDrawer tab (spec-111 C2). This is
 * the "where is the class war hottest" ranked/textual breakdown of every
 * live relationship edge in the graph (exploitation, wages, solidarity,
 * tenancy, tribute...) — the companion to the already-shipped `field_flow`
 * spatial lens: the shape of the relations, plus the top edges by tension
 * and by value flow.
 *
 * Mirrors `StateApparatusDashboard` exactly: same panel shape
 * (`panels.edges`, `PANEL_KEYS`-fanned-out), same
 * setMounted(true)/fetch-on-mount/setMounted(false)-on-unmount idiom, same
 * `BottomDrawer` tab-row mechanism (`ui.chrome.bottomDrawer`'s `"edges"`
 * arm) rather than a new UI location.
 *
 * Honest-null throughout (Constitution III.11): `counts_by_mode` is
 * legitimately `{}` until `EdgeTransitionSystem` has run at least one tick
 * (a fresh tick-0 graph has no dialectical edge_mode classification yet),
 * and `solidarity_strength_stats`'s `avg`/`min`/`max` are `null` when no
 * SOLIDARITY edge exists this session — both render an explicit honest
 * note, never a fabricated placeholder.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { StatChip } from "@/components/shell/StatChip";
import type { EdgeRow } from "@/types/game";

interface EdgesDashboardProps {
  gameId: string;
}

function SectionLabel({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">{children}</p>;
}

/**
 * `tension` is a bounded [0,1] `Intensity`
 * (`relationship_state.py`'s `tension: float = Field(ge=0.0, le=1.0)`) —
 * bucketed onto the app's existing threat palette so the hottest rows in a
 * tension-ranked list read as hot at a glance, cooling toward `text-bone`
 * as tension falls.
 */
function tensionColor(tension: number): string {
  if (tension >= 0.66) return "text-laser";
  if (tension >= 0.33) return "text-heat";
  return "text-bone";
}

/**
 * Compact edge-type / edge-mode breakdown — "the shape of the relations."
 * Sorted by count descending (busiest relation first). Reused for both
 * `counts_by_type` (mechanical) and `counts_by_mode` (dialectical) since
 * both are `Record<string, number>` with the same rendering need; the
 * empty state (a legitimately-empty `counts_by_mode` at tick 0) is the
 * caller's concern via `emptyLabel`.
 */
function EdgeCountsBreakdown({
  counts,
  testId,
  emptyLabel,
}: {
  counts: Record<string, number>;
  testId: string;
  emptyLabel: string;
}): React.JSX.Element {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid={`${testId}-empty`}>
        {emptyLabel}
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5" data-testid={testId}>
      {entries.map(([type, count]) => (
        <div
          key={type}
          data-testid={`${testId}-${type}`}
          className="flex items-center gap-1 text-[11px]"
        >
          <span className="text-bone">{type}</span>
          <span className="font-mono text-ash">{count}</span>
        </div>
      ))}
    </div>
  );
}

type RankedMetric = "tension" | "value_flow";

/**
 * The ranked edge list — "columns" source→target, edge_type, tension,
 * value_flow, always rendered together (an `<ol>` of flex rows, matching
 * `StateApparatusDashboard`'s `ActionFeed`/`StateOrgList` idiom rather than
 * a literal HTML `<table>`, since nothing else in this app uses one).
 * `emphasize` bolds + color-codes whichever metric this particular
 * section is ranked by, so "Hottest Edges" and "Top Value Flow" read
 * distinctly even though every row carries both numbers.
 */
function EdgeRankedList({
  rows,
  emphasize,
  testId,
  emptyLabel,
}: {
  rows: EdgeRow[];
  emphasize: RankedMetric;
  testId: string;
  emptyLabel: string;
}): React.JSX.Element {
  if (rows.length === 0) {
    return (
      <p className="text-[11px] italic text-shroud" data-testid={`${testId}-empty`}>
        {emptyLabel}
      </p>
    );
  }

  return (
    <ol className="flex flex-col gap-1" data-testid={testId}>
      {rows.map((row) => (
        <li
          key={`${row.source_id}-${row.target_id}`}
          data-testid={`${testId}-row-${row.source_id}-${row.target_id}`}
          className="flex items-center gap-2 text-[11px]"
        >
          <span className="flex-1 truncate font-mono text-[10px] text-bone">
            {row.source_id} → {row.target_id}
          </span>
          <span className="font-mono text-[9px] uppercase text-ash">{row.edge_type}</span>
          <span
            className={`font-mono text-[10px] ${
              emphasize === "tension" ? `font-semibold ${tensionColor(row.tension)}` : "text-ash"
            }`}
          >
            tension {row.tension.toFixed(2)}
          </span>
          <span
            className={`font-mono text-[10px] ${
              emphasize === "value_flow" ? "font-semibold text-cadre" : "text-ash"
            }`}
          >
            flow {row.value_flow.toFixed(1)}
          </span>
        </li>
      ))}
    </ol>
  );
}

export function EdgesDashboard({ gameId }: EdgesDashboardProps): React.JSX.Element {
  const data = useStore((s) => s.panels.edges.data);
  const loading = useStore((s) => s.panels.edges.loading);
  const error = useStore((s) => s.panels.edges.error);
  const fetchEdges = useStore((s) => s.panels.edges.fetch);
  const setMounted = useStore((s) => s.panels.edges.setMounted);

  useEffect(() => {
    setMounted(true);
    void fetchEdges(gameId);
    return () => setMounted(false);
  }, [gameId, fetchEdges, setMounted]);

  if (loading && data === null) {
    return <p className="p-3 text-[11px] text-ash">Loading edges…</p>;
  }
  if (error) {
    return (
      <p role="alert" className="p-3 text-[11px] text-laser">
        {error}
      </p>
    );
  }
  if (data === null) {
    return (
      <p className="p-3 text-[11px] italic text-shroud" data-testid="edges-no-data">
        No edges data yet.
      </p>
    );
  }

  const solidarity = data.solidarity_strength_stats;

  return (
    <div className="flex flex-col gap-3 p-2" data-testid="edges-dashboard">
      <div className="flex flex-wrap gap-1.5" data-testid="edges-stat-chips">
        <StatChip label="Total Edges" value={data.total_edges} format={(v) => v.toFixed(0)} />
        <StatChip
          label="Solidarity Edges"
          value={solidarity.count}
          format={(v) => v.toFixed(0)}
          colorClassName="text-solidarity"
        />
        <StatChip
          label="Avg Solidarity Strength"
          value={solidarity.avg}
          format={(v) => v.toFixed(3)}
          colorClassName="text-solidarity"
        />
      </div>
      {solidarity.count === 0 && (
        <p className="text-[11px] italic text-shroud" data-testid="edges-solidarity-empty">
          No solidarity edges this session.
        </p>
      )}

      <div>
        <SectionLabel>Relations by Type</SectionLabel>
        <EdgeCountsBreakdown
          counts={data.counts_by_type}
          testId="edges-type-breakdown"
          emptyLabel="No edges in this graph yet."
        />
      </div>

      <div>
        <SectionLabel>Edge Modes (Dialectical)</SectionLabel>
        <EdgeCountsBreakdown
          counts={data.counts_by_mode}
          testId="edges-mode-breakdown"
          emptyLabel="Edge modes not yet classified (EdgeTransitionSystem)."
        />
      </div>

      <div>
        <SectionLabel>Hottest Edges (by Tension)</SectionLabel>
        <EdgeRankedList
          rows={data.top_by_tension}
          emphasize="tension"
          testId="edges-ranked-tension"
          emptyLabel="No ranked edges yet."
        />
      </div>

      <div>
        <SectionLabel>Top Value Flow</SectionLabel>
        <EdgeRankedList
          rows={data.top_by_value_flow}
          emphasize="value_flow"
          testId="edges-ranked-value-flow"
          emptyLabel="No ranked edges yet."
        />
      </div>
    </div>
  );
}
