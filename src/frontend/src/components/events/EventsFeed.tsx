/**
 * Events feed — classified events for the *current* tick only
 * (`WorldState.events` is per-tick, not cumulative — a tick with no
 * events is `[]`, never carried forward). Clicking an event selects its
 * linked entity — the "autopause deep-link": when the time slice
 * autopauses on a critical event, clicking that event in the feed drives
 * the Inspector + map highlight straight to what triggered it.
 */

import { useStore } from "@/store";
import { classifyEvents } from "@/lib/eventClassifier";
import { inspectorKindForEvent } from "@/lib/inspectorMapping";
import type { ClassifiedEvent, EventSeverity } from "@/types/game";

const SEVERITY_COLOR: Record<EventSeverity, string> = {
  critical: "text-laser",
  important: "text-heat",
  informational: "text-solidarity",
};

export function EventsFeed(): React.JSX.Element {
  const events = useStore((s) => s.world.snapshot?.events);
  const autopauseEventIds = useStore((s) => s.time.autopauseEventIds);
  const setSelection = useStore((s) => s.map.setSelection);

  const classified = classifyEvents(events ?? []);

  if (!events) {
    return <p className="p-3 text-[11px] italic text-shroud">No world state loaded yet.</p>;
  }
  if (classified.length === 0) {
    return <p className="p-3 text-[11px] italic text-shroud">No events this tick.</p>;
  }

  function handleClick(event: ClassifiedEvent): void {
    const kind = inspectorKindForEvent(event);
    if (kind && event.linkedEntityId) {
      setSelection({ kind, id: event.linkedEntityId });
    }
  }

  return (
    <div className="flex flex-col gap-1 p-2" data-testid="events-feed">
      {classified.map((e) => (
        <button
          key={e.id}
          onClick={() => handleClick(e)}
          disabled={!e.linkedEntityId}
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
