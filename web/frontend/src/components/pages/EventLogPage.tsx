/**
 * EventLogPage — the full cross-tick classified event history.
 *
 * Spec 092: replaces the `/games/:id/log` "coming soon" stub. Ports the
 * severity-filter + scrolling-row design of
 * `design/mockups/ui_kits/webapp/EventLog.jsx` (design reference only —
 * this is fresh code against the real `useJournal` contract, not a port
 * of the mockup's JSX). Fed by `GET /api/games/:id/journal/`
 * (`EngineBridge.get_journal_dashboard`) and classified via the existing
 * `lib/eventClassifier.ts` (shared with the notification tray).
 */

import { useMemo, useState } from "react";
import { useParams } from "react-router";
import { BblBadge, BblPanel } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { useJournal } from "@/hooks/useJournal";
import { classifyEvents } from "@/lib/eventClassifier";
import type { EventSeverity, GameEvent } from "@/types/game";

type FilterOption = "all" | EventSeverity;

const FILTERS: FilterOption[] = ["all", "informational", "important", "critical"];

/** Severity → badge color token (matches BriefingPage's Priority Dispatch). */
function severityColor(severity: EventSeverity): string {
  switch (severity) {
    case "critical":
      return "#e04040";
    case "important":
      return "#e0a030";
    case "informational":
    default:
      return "#787878";
  }
}

function subtitleFor(loading: boolean, error: string | null, count: number): string {
  if (loading) return "Loading…";
  if (error) return `Error: ${error}`;
  return `${count} events recorded`;
}

function EventRow({ event, severity }: { event: GameEvent; severity: EventSeverity }) {
  const color = severityColor(severity);
  return (
    <div
      className="flex items-baseline gap-3 border-b border-soot/50 px-3 py-2 hover:bg-soot/30"
      style={{ borderLeft: `2px solid ${color}` }}
    >
      <span className="w-12 shrink-0 font-mono text-[10px] text-ash">t={event.tick}</span>
      <span className="w-32 shrink-0 truncate font-mono text-[10px] uppercase tracking-wider text-fog">
        {event.type}
      </span>
      <span className="flex-1 text-[12px] text-bone">{event.body || event.title}</span>
      <BblBadge color={color}>{severity}</BblBadge>
    </div>
  );
}

export function EventLogPage() {
  const { id: gameId } = useParams<{ id: string }>();
  const { data, loading, error } = useJournal(gameId ?? null);
  const [filter, setFilter] = useState<FilterOption>("all");

  const classified = useMemo(() => classifyEvents(data.events), [data.events]);

  const filtered = filter === "all" ? classified : classified.filter((c) => c.severity === filter);

  const subtitle = subtitleFor(loading, error, data.events.length);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Event Log"
        subtitle={subtitle}
        breadcrumbs={["Operation", "Event Log"]}
        right={
          <div className="flex gap-1">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded border px-2 py-1 font-mono text-[9px] uppercase tracking-wider transition-colors ${
                  filter === f
                    ? "border-gold text-gold"
                    : "border-soot text-ash hover:border-wet-concrete"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        }
      />

      <div className="min-h-0 flex-1 overflow-auto p-3">
        <BblPanel title="History" right={<BblBadge color="#787878">{filtered.length}</BblBadge>}>
          {filtered.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm text-ash">
              No events recorded yet
            </div>
          ) : (
            <div className="flex flex-col">
              {filtered.map((c) => (
                <EventRow key={c.id} event={c.event} severity={c.severity} />
              ))}
            </div>
          )}
        </BblPanel>
      </div>
    </div>
  );
}
