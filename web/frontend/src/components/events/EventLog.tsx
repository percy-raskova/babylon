/**
 * Event log — scrolling color-coded feed of simulation events.
 *
 * Displays events from the current snapshot plus accumulated events
 * from the game store's tick history.
 */

import { useRef, useEffect } from "react";
import type { GameEvent, GameSnapshot } from "@/types/game";
import { useGameStore } from "@/stores/gameStore";

interface EventLogProps {
  snapshot: GameSnapshot;
}

/** Color mapping for event types. */
const EVENT_COLORS: Record<string, string> = {
  // Economic
  EXTRACTION: "text-crimson",
  IMPERIAL_RENT: "text-crimson",
  WAGES_PAID: "text-data-green",
  VALUE_TRANSFER: "text-gold",
  // Consciousness / solidarity
  CONSCIOUSNESS_SHIFT: "text-gold",
  SOLIDARITY_FORMED: "text-royal-blue",
  SOLIDARITY_BROKEN: "text-phosphor-red",
  BIFURCATION: "text-warning-amber",
  // Struggle
  UPRISING: "text-crimson",
  EXCESSIVE_FORCE: "text-phosphor-red",
  RUPTURE: "text-crimson",
  // Territory
  EVICTION: "text-phosphor-red",
  HEAT_SPIKE: "text-warning-amber",
  // Organization
  ORG_FORMED: "text-grow-purple",
  ORG_DISSOLVED: "text-ash",
  ACTION_RESULT: "text-royal-blue",
  // Institution
  FACTION_SHIFT: "text-silver",
  BONAPARTIST_MODE: "text-gold",
  // Phase transitions
  PHASE_TRANSITION: "text-gold",
  PERCOLATION: "text-data-green",
};

/** Icon/prefix for event types. */
const EVENT_ICONS: Record<string, string> = {
  UPRISING: "!!",
  EXCESSIVE_FORCE: "!!",
  RUPTURE: "!!",
  EVICTION: "!",
  BIFURCATION: "~",
  PHASE_TRANSITION: ">>",
  BONAPARTIST_MODE: "**",
};

export function EventLog({ snapshot }: EventLogProps) {
  const tickSummaries = useGameStore((s) => s.tickSummaries);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [snapshot.events.length, tickSummaries.length]);

  const events = snapshot.events;

  if (events.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ash">
        No events recorded yet
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="h-full overflow-auto font-mono text-[11px] leading-relaxed">
      {events.map((event, i) => (
        <EventRow key={`${event.tick}-${event.type}-${i}`} event={event} />
      ))}
    </div>
  );
}

function EventRow({ event }: { event: GameEvent }) {
  const color = EVENT_COLORS[event.type] ?? "text-ash";
  const icon = EVENT_ICONS[event.type] ?? "--";

  // Build a concise message from event data
  const message = formatEventMessage(event);

  return (
    <div className="flex gap-2 border-b border-soot/50 px-1 py-0.5 hover:bg-soot/30">
      <span className="shrink-0 text-ash">T{event.tick}</span>
      <span className={`shrink-0 ${color}`}>{icon}</span>
      <span className={`shrink-0 font-semibold ${color}`}>{event.type}</span>
      <span className="truncate text-bone/70">{message}</span>
    </div>
  );
}

/** Format event data into a human-readable summary string. */
function formatEventMessage(event: GameEvent): string {
  const d = event.data;
  const parts: string[] = [];

  // Common fields across event types
  if (typeof d.source === "string") parts.push(`from:${d.source}`);
  if (typeof d.target === "string") parts.push(`to:${d.target}`);
  if (typeof d.source_id === "string") parts.push(`from:${d.source_id}`);
  if (typeof d.target_id === "string") parts.push(`to:${d.target_id}`);
  if (typeof d.entity_id === "string") parts.push(d.entity_id);
  if (typeof d.territory_id === "string") parts.push(d.territory_id);
  if (typeof d.org_id === "string") parts.push(d.org_id);
  if (typeof d.amount === "number") parts.push(`amt:${d.amount.toFixed(1)}`);
  if (typeof d.delta === "number") parts.push(`delta:${d.delta.toFixed(2)}`);
  if (typeof d.value === "number") parts.push(`val:${d.value.toFixed(2)}`);
  if (typeof d.success === "boolean") parts.push(d.success ? "OK" : "FAIL");
  if (typeof d.message === "string") parts.push(d.message);

  return parts.join(" | ");
}
