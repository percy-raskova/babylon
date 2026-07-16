/**
 * DoctrineTakeover — the Doctrine Tree canvas (Epoch 3 Wave 6 Phase 0, the
 * 5th takeover). Renders the static 11-node MVP tree (`useDoctrineTree`,
 * one-shot-fetched on open, mirrors `useOrgNetwork`'s mount/fetch idiom) by
 * tier (0->4) and by strategic trunk (reformist / scientific /
 * insurrectionist columns) — matches
 * `ai/epochs/epoch3/doctrine-tree-mvp.yaml`'s
 * `ui_requirements.doctrine_panel.ascii_mockup` layout, as a tiered/trunked
 * grid rather than literal connector lines (the spec's explicitly-permitted
 * "clean indented/columned tree" fallback).
 *
 * LIVE + INTERACTIVE (Unit 7b): the DoctrineSystem now advances each faction's
 * doctrine every tick, so this canvas overlays the player faction's REAL state —
 * acquired nodes are lit (ring + "Acquired"), the theoretical-labour balance and
 * the decaying tag accumulator are shown live. Unacquired, non-trap nodes render
 * a Study affordance that submits the standing Study order through the existing
 * educate verb (`POST /api/games/{id}/actions/educate/`, `educateConfig.buildPayload`)
 * — it queues for the next tick, the DoctrineSystem honors the order on
 * subsequent ticks rather than acquiring instantly. The ordered node shows a
 * "Studying" badge and its footer reads "Study ordered" instead of a button.
 * Acquired nodes, trap nodes, and — when the session has no player faction
 * (`faction_id: null`) — every node render no button at all: honestly LOCKED
 * with their real cost, never a fake affordance (Constitution III.11).
 */

import { useMemo, useState } from "react";
import { useDoctrineTree } from "@/hooks/useDoctrineTree";
import { post as apiPost } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import { educateConfig } from "@/lib/verbs/educate";
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

/** A node's Study affordance state — see `nodeStudyState`. */
type StudyState = "none" | "studyable" | "ordered";

/**
 * Node action state, derived once per card. A node is a Study affordance
 * only when the session has a player faction, the node isn't already
 * acquired, and it isn't a trap (Constitution III.11 — never a fake or
 * self-defeating affordance). The node currently under the standing Study
 * order renders its "ordered" state instead of a button.
 */
function nodeStudyState(
  node: DoctrineNode,
  acquired: boolean,
  factionId: string | null,
  studyTargetId: string | null,
): StudyState {
  if (acquired || node.is_trap || factionId === null) return "none";
  return node.id === studyTargetId ? "ordered" : "studyable";
}

/** Footer status text for a non-button card state — "Acquired" takes
 *  priority (an acquired node is never mid-study), otherwise honest
 *  "Study ordered" / "Locked". */
function footerStatusText(acquired: boolean, studyState: StudyState): string {
  if (acquired) return "Acquired";
  if (studyState === "ordered") return "Study ordered";
  return "Locked";
}

/** Footer status text color — mirrors `footerStatusText`'s priority. */
function footerStatusClass(acquired: boolean, studyState: StudyState): string {
  if (acquired) return "text-rupture";
  if (studyState === "ordered") return "text-heat";
  return "text-ksbc-muted-1";
}

function NodeCard({
  node,
  acquired,
  factionId,
  studyTargetId,
  studySubmitting,
  onStudy,
}: {
  node: DoctrineNode;
  acquired: boolean;
  factionId: string | null;
  studyTargetId: string | null;
  studySubmitting: boolean;
  onStudy: (node: DoctrineNode) => void;
}): React.JSX.Element {
  const borderClass = acquired && !node.is_trap ? "border-rupture" : nodeBorderClass(node);
  const tagEntries = Object.entries(node.tag_deltas) as [DoctrineTagKey, number][];
  const studyState = nodeStudyState(node, acquired, factionId, studyTargetId);

  return (
    <div
      className={`flex flex-col gap-1 border-2 bg-plate p-2 ${borderClass} ${
        acquired ? "ring-1 ring-rupture" : ""
      }`}
      data-testid={`doctrine-node-${node.id}`}
      data-acquired={acquired}
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
        {studyState === "ordered" && (
          <span className="border border-heat px-1 text-[8px] uppercase tracking-widest text-heat">
            Studying
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
        {studyState === "studyable" ? (
          <button
            type="button"
            onClick={() => onStudy(node)}
            disabled={studySubmitting}
            data-testid={`doctrine-study-${node.id}`}
            className="bg-transparent p-0 uppercase tracking-widest text-heat underline decoration-dotted underline-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Study {node.name}
          </button>
        ) : (
          <span className={`uppercase tracking-widest ${footerStatusClass(acquired, studyState)}`}>
            {footerStatusText(acquired, studyState)}
          </span>
        )}
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
function TierRow({
  tier,
  nodes,
  acquired,
  factionId,
  studyTargetId,
  studySubmitting,
  onStudy,
}: {
  tier: number;
  nodes: DoctrineNode[];
  acquired: Set<string>;
  factionId: string | null;
  studyTargetId: string | null;
  studySubmitting: boolean;
  onStudy: (node: DoctrineNode) => void;
}): React.JSX.Element {
  const isShared = nodes.every((node) => node.trunk === null);

  return (
    <div data-testid={`doctrine-tier-${tier}`}>
      <span className="text-[8px] uppercase tracking-widest text-ksbc-muted-1">Tier {tier}</span>
      {isShared ? (
        <div className="mx-auto mt-1 flex max-w-xs flex-col gap-2">
          {nodes.map((node) => (
            <NodeCard
              key={node.id}
              node={node}
              acquired={acquired.has(node.id)}
              factionId={factionId}
              studyTargetId={studyTargetId}
              studySubmitting={studySubmitting}
              onStudy={onStudy}
            />
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
                {node && (
                  <NodeCard
                    node={node}
                    acquired={acquired.has(node.id)}
                    factionId={factionId}
                    studyTargetId={studyTargetId}
                    studySubmitting={studySubmitting}
                    onStudy={onStudy}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function DoctrineTakeover({ gameId }: Props): React.JSX.Element {
  const { data, loading, error, refresh } = useDoctrineTree(gameId);
  const [studySubmitting, setStudySubmitting] = useState(false);
  const [studyError, setStudyError] = useState<string | null>(null);

  async function handleStudy(node: DoctrineNode): Promise<void> {
    const factionId = data.faction_id;
    if (!factionId) return;
    setStudySubmitting(true);
    setStudyError(null);
    const body = educateConfig.buildPayload(factionId, factionId, {
      doctrine_node_id: node.id,
    });
    const res = await apiPost(endpoints.educateSubmit.path({ id: gameId }), body);
    setStudySubmitting(false);
    if (res.status === "ok") {
      await refresh();
    } else {
      setStudyError(res.message ?? "Failed to submit the Study order");
    }
  }

  const tiers = useMemo(() => {
    const grouped = groupByTier(data.nodes);
    return Array.from(grouped.keys())
      .sort((a, b) => a - b)
      .map((tier) => ({ tier, nodes: grouped.get(tier) ?? [] }));
  }, [data.nodes]);

  const tagEntries = Object.entries(data.tags) as [DoctrineTagKey, number][];
  const isEmpty = data.nodes.length === 0;
  const acquiredSet = useMemo(() => new Set(data.acquired_ids), [data.acquired_ids]);

  return (
    <div className="flex h-full w-full flex-col" data-testid="doctrine-takeover">
      <header className="flex flex-col gap-2 border-b-2 border-ksbc-muted-1 px-3 py-2">
        <p className="text-[10px] italic text-ksbc-muted-2" data-testid="doctrine-acquisition-note">
          The Party&rsquo;s live doctrine — acquired nodes are lit; theory decays without study.
          Click Study on an unlocked node to direct the Party&rsquo;s theoretical labour.
        </p>
        {studyError && (
          <p role="alert" className="text-[10px] text-laser" data-testid="doctrine-study-error">
            {studyError}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-mono text-[11px] uppercase tracking-widest text-ksbc-muted-2">
            {acquiredSet.size}/{data.nodes.length} acquired
          </span>
          <span
            className="font-mono text-[11px] uppercase tracking-widest text-rupture"
            data-testid="doctrine-theoretical-labor"
          >
            {data.theoretical_labor.toFixed(1)} TL
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
              <TierRow
                key={tier}
                tier={tier}
                nodes={nodes}
                acquired={acquiredSet}
                factionId={data.faction_id}
                studyTargetId={data.study_target_id}
                studySubmitting={studySubmitting}
                onStudy={(node) => void handleStudy(node)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
