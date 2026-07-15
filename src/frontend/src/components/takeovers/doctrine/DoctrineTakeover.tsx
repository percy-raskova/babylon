/**
 * DoctrineTakeover — the read-only Doctrine Tree canvas (Epoch 3 Wave 6
 * Phase 0, the 5th takeover). Renders the static 11-node MVP tree
 * (`useDoctrineTree`, one-shot-fetched on open, mirrors `useOrgNetwork`'s
 * mount/fetch idiom) by tier (0->4) and by strategic trunk (reformist /
 * scientific / insurrectionist columns) — matches
 * `ai/epochs/epoch3/doctrine-tree-mvp.yaml`'s
 * `ui_requirements.doctrine_panel.ascii_mockup` layout, as a tiered/trunked
 * grid rather than literal connector lines (the spec's explicitly-permitted
 * "clean indented/columned tree" fallback).
 *
 * READ-ONLY: acquisition/TL-spend/Party Congress/DoctrineSystem engine
 * wiring is gated on six pending owner rulings and explicitly out of scope
 * here. Every node renders LOCKED with its cost — never a fake "acquire"
 * affordance (Constitution III.11). `acquired_ids` is always `[]` from the
 * backend today, so there is no "acquired" visual state to render; the
 * header note says so explicitly rather than staying silent about it.
 */

import { useMemo } from "react";
import { useDoctrineTree } from "@/hooks/useDoctrineTree";
import type { DoctrineNode, DoctrineTagKey, DoctrineTrunkKey } from "@/types/game";

interface Props {
  gameId: string;
}

const TRUNKS: DoctrineTrunkKey[] = ["reformist", "scientific", "insurrectionist"];

const TRUNK_LABEL: Record<DoctrineTrunkKey, string> = {
  reformist: "Reformist",
  scientific: "Scientific",
  insurrectionist: "Insurrectionist",
};

const TAG_LABEL: Record<DoctrineTagKey, string> = {
  class_analysis: "Class Analysis",
  mass_link: "Mass Link",
  militancy: "Militancy",
};

const TAG_MAX = 10;

/** A tag's current value as a filled bar out of `TAG_MAX` — mirrors the
 *  corpus ascii mockup's "CLASS_ANALYSIS: ###....  3" gauge, using the same
 *  bg-rebar/colored-fill grammar `BreakdownBar` already established. */
function TagMeter({ tagKey, value }: { tagKey: DoctrineTagKey; value: number }): React.JSX.Element {
  const pct = Math.max(0, Math.min(100, (value / TAG_MAX) * 100));
  return (
    <div className="flex items-center gap-2" data-testid={`doctrine-tag-${tagKey}`}>
      <span className="w-24 shrink-0 text-[9px] uppercase tracking-widest text-ksbc-muted-2">
        {TAG_LABEL[tagKey]}
      </span>
      <div className="h-1.5 w-20 overflow-hidden rounded-sm bg-rebar">
        <div className="h-full bg-solidarity" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-ink">{value}</span>
    </div>
  );
}

/** One `tag_deltas` entry on a node card — green for a positive contribution,
 *  laser-red for a negative one (the same polarity convention the rest of
 *  the cockpit uses for gain/loss). */
function TagDelta({ tagKey, delta }: { tagKey: DoctrineTagKey; delta: number }): React.JSX.Element {
  const sign = delta > 0 ? "+" : "";
  return (
    <span className={delta >= 0 ? "text-solidarity" : "text-laser"}>
      {TAG_LABEL[tagKey]} {sign}
      {delta}
    </span>
  );
}

/** Honest cost label: the root is free, a trap is "fallen into" (never
 *  purchased — `cost_tl` is 0 for a different reason than the root's), and
 *  everything else shows its real TL cost. */
function costLabel(node: DoctrineNode): string {
  if (node.is_trap) return "Fallen into — not purchased";
  if (node.cost_tl === 0) return "FREE";
  return `${node.cost_tl} TL`;
}

/** Border color by node state — trap (danger) takes priority over goal
 *  (a node is never both), everything else is neutral. */
function nodeBorderClass(node: DoctrineNode): string {
  if (node.is_trap) return "border-laser";
  if (node.is_goal) return "border-rupture";
  return "border-ksbc-muted-1";
}

function NodeCard({ node }: { node: DoctrineNode }): React.JSX.Element {
  const borderClass = nodeBorderClass(node);
  const tagEntries = Object.entries(node.tag_deltas) as [DoctrineTagKey, number][];

  return (
    <div
      className={`flex flex-col gap-1 border-2 bg-plate p-2 ${borderClass}`}
      data-testid={`doctrine-node-${node.id}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] font-semibold text-ink">{node.name}</span>
        {node.is_trap && (
          <span className="border border-laser px-1 text-[8px] uppercase tracking-widest text-laser">
            Trap
          </span>
        )}
        {node.is_goal && (
          <span className="border border-rupture px-1 text-[8px] uppercase tracking-widest text-rupture">
            Goal
          </span>
        )}
      </div>
      <p className="text-[10px] text-ksbc-muted-2">{node.description}</p>
      {tagEntries.length > 0 && (
        <div className="flex flex-wrap gap-x-2 gap-y-0.5 font-mono text-[9px]">
          {tagEntries.map(([tagKey, delta]) => (
            <TagDelta key={tagKey} tagKey={tagKey} delta={delta} />
          ))}
        </div>
      )}
      {node.warning && (
        <p className="text-[9px] italic text-heat" data-testid={`doctrine-warning-${node.id}`}>
          {node.warning}
        </p>
      )}
      {node.narrative && (
        <p className="whitespace-pre-line text-[9px] italic text-ksbc-muted-2">{node.narrative}</p>
      )}
      <div className="mt-auto flex items-center justify-between pt-1 text-[9px]">
        <span className="uppercase tracking-widest text-ksbc-muted-1">Locked</span>
        <span className="font-mono text-ksbc-muted-2">{costLabel(node)}</span>
      </div>
    </div>
  );
}

/** Group nodes by `tier` — pure/data-driven, no hardcoded node ids. */
function groupByTier(nodes: DoctrineNode[]): Map<number, DoctrineNode[]> {
  const map = new Map<number, DoctrineNode[]>();
  for (const node of nodes) {
    const bucket = map.get(node.tier) ?? [];
    bucket.push(node);
    map.set(node.tier, bucket);
  }
  return map;
}

/**
 * One tier row. A tier whose nodes are ALL pre-split (`trunk === null`,
 * e.g. the MVP's root + shared `trade_unionism`) renders as a single
 * centered column; once a tier has trunk-tagged nodes it renders as a
 * 3-column grid, one card per trunk (a trunk with no node at this tier
 * renders an empty cell rather than a fabricated placeholder card).
 */
function TierRow({ tier, nodes }: { tier: number; nodes: DoctrineNode[] }): React.JSX.Element {
  const isShared = nodes.every((node) => node.trunk === null);

  return (
    <div data-testid={`doctrine-tier-${tier}`}>
      <span className="text-[8px] uppercase tracking-widest text-ksbc-muted-1">Tier {tier}</span>
      {isShared ? (
        <div className="mx-auto mt-1 flex max-w-xs flex-col gap-2">
          {nodes.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
        </div>
      ) : (
        <div className="mt-1 grid grid-cols-3 gap-3">
          {TRUNKS.map((trunk) => {
            const node = nodes.find((n) => n.trunk === trunk);
            return (
              <div key={trunk} className="flex flex-col gap-1">
                <span className="text-center text-[8px] uppercase tracking-widest text-ksbc-muted-1">
                  {TRUNK_LABEL[trunk]}
                </span>
                {node && <NodeCard node={node} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function DoctrineTakeover({ gameId }: Props): React.JSX.Element {
  const { data, loading, error } = useDoctrineTree(gameId);

  const tiers = useMemo(() => {
    const grouped = groupByTier(data.nodes);
    return Array.from(grouped.keys())
      .sort((a, b) => a - b)
      .map((tier) => ({ tier, nodes: grouped.get(tier) ?? [] }));
  }, [data.nodes]);

  const tagEntries = Object.entries(data.tags) as [DoctrineTagKey, number][];
  const isEmpty = data.nodes.length === 0;

  return (
    <div className="flex h-full w-full flex-col" data-testid="doctrine-takeover">
      <header className="flex flex-col gap-2 border-b-2 border-ksbc-muted-1 px-3 py-2">
        <p className="text-[10px] italic text-ksbc-muted-2" data-testid="doctrine-acquisition-note">
          Doctrine acquisition unlocks with the Party (coming). This canvas is read-only.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-mono text-[11px] uppercase tracking-widest text-ksbc-muted-2">
            {data.nodes.length} nodes
          </span>
          <div className="flex flex-wrap gap-3" data-testid="doctrine-tags">
            {tagEntries.map(([tagKey, value]) => (
              <TagMeter key={tagKey} tagKey={tagKey} value={value} />
            ))}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {loading && isEmpty && <p className="p-3 text-[11px] text-ash">Loading doctrine tree…</p>}
        {error && (
          <p role="alert" className="p-3 text-[11px] text-laser">
            {error}
          </p>
        )}
        {!loading && !error && isEmpty && (
          <p className="p-3 text-[11px] italic text-shroud" data-testid="doctrine-empty">
            No doctrine tree data available.
          </p>
        )}
        {!isEmpty && (
          <div className="flex flex-col gap-4">
            {tiers.map(({ tier, nodes }) => (
              <TierRow key={tier} tier={tier} nodes={nodes} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
