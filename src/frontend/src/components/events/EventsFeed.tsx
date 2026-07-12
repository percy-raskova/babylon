/**
 * Events feed — classified events for the *current* tick only
 * (`WorldState.events` is per-tick, not cumulative — a tick with no
 * events is `[]`, never carried forward). Clicking an event selects its
 * linked entity — the "autopause deep-link": when the time slice
 * autopauses on a critical event, clicking that event in the feed drives
 * the Inspector + map highlight straight to what triggered it.
 *
 * A critical event with no linked entity (e.g. `rupture` — an
 * existential state change, not a territory/org action) has nothing for
 * the Inspector to show; clicking it opens the Chronicle takeover instead
 * (spec-110 B5) — the closest read of "where the old app did" deep-link
 * for a critical event this feed can't otherwise resolve.
 */

import { useStore } from "@/store";
import { classifyEvents } from "@/lib/eventClassifier";
import type { InspectorKind } from "@/store";
import type { ClassifiedEvent, EventSeverity } from "@/types/game";

const SEVERITY_COLOR: Record<EventSeverity, string> = {
  critical: "text-laser",
  important: "text-heat",
  informational: "text-solidarity",
};

/**
 * Maps a classified event's linked-entity type to the Inspector's
 * `InspectorKind` — the join between the events feed and
 * `mapSlice.setSelection` (spec-110 B3 stage 2's "autopause deep-link":
 * clicking an event selects the entity it references). Absorbed from
 * `lib/inspectorMapping.ts` (spec-113 Lane G) — this was its one consumer.
 *
 * `institution` has no dedicated `InspectorKind` (the inspector endpoint
 * set is `node | org | community | edge | hex`) — it falls back to the
 * generic `node` kind rather than being silently dropped.
 */
const LINKED_ENTITY_TO_INSPECTOR_KIND: Record<
  NonNullable<ClassifiedEvent["linkedEntityType"]>,
  InspectorKind
> = {
  territory: "hex",
  organization: "org",
  institution: "node",
  hyperedge: "community",
};

/** Resolve the `InspectorKind` a classified event's linked entity maps to, or `null` if unlinked. */
function inspectorKindForEvent(event: ClassifiedEvent): InspectorKind | null {
  if (!event.linkedEntityType || !event.linkedEntityId) return null;
  return LINKED_ENTITY_TO_INSPECTOR_KIND[event.linkedEntityType];
}

export function EventsFeed(): React.JSX.Element {
  const events = useStore((s) => s.world.snapshot?.events);
  const autopauseEventIds = useStore((s) => s.time.autopauseEventIds);
  const setSelection = useStore((s) => s.map.setSelection);
  const openTakeover = useStore((s) => s.ui.openTakeover);

  const classified = classifyEvents(events ?? []);

  // The honest empty states carry the same testid as the populated feed —
  // "renders classified events OR the honest empty copy" is one surface
  // (Constitution III.11), and e2e asserts on the container either way.
  // Copy is in-register (DESIGN_BIBLE §7's "purge the admin voice" — "the
  // wire is silent", not "No events loaded yet.").
  if (!events) {
    return (
      <div className="flex flex-col gap-1 p-2" data-testid="events-feed">
        <p className="p-3 text-[11px] italic text-shroud">The wire is silent — no dispatch yet.</p>
      </div>
    );
  }
  if (classified.length === 0) {
    return (
      <div className="flex flex-col gap-1 p-2" data-testid="events-feed">
        <p className="p-3 text-[11px] italic text-shroud">The wire is quiet this tick.</p>
      </div>
    );
  }

  function handleClick(event: ClassifiedEvent): void {
    const kind = inspectorKindForEvent(event);
    if (kind && event.linkedEntityId) {
      setSelection({ kind, id: event.linkedEntityId });
      return;
    }
    if (event.severity === "critical") {
      openTakeover("chronicle");
    }
  }

  return (
    <div className="flex flex-col gap-1 p-2" data-testid="events-feed">
      {classified.map((e) => (
        <button
          key={e.id}
          onClick={() => handleClick(e)}
          disabled={!e.linkedEntityId && e.severity !== "critical"}
          data-testid={`event-${e.id}`}
          data-autopause={autopauseEventIds.includes(e.id) || undefined}
          className="flex items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-rebar disabled:cursor-default disabled:hover:bg-transparent"
        >
          <span className={`text-[10px] ${SEVERITY_COLOR[e.severity]}`}>●</span>
          <span className="min-w-[90px] font-mono text-[9px] uppercase tracking-widest text-ash">
            {e.event.type}
          </span>
          <span className="flex-1 truncate text-[11px] text-bone">
            {e.event.title || e.event.body || e.event.type}
          </span>
        </button>
      ))}
    </div>
  );
}
