/**
 * Event log — scrolling color-coded feed of simulation events.
 *
 * Supports two modes:
 * 1. Raw event feed (events tab) — all events from current snapshot
 * 2. Notification groups (notifications tab) — classified and grouped events from uiStore
 */

import { useRef, useEffect } from "react";
import { useUIStore } from "@/stores/uiStore";
import { useGameStore } from "@/stores/gameStore";
import type { GameEvent, GameSnapshot, NotificationGroup } from "@/types/game";

interface EventLogProps {
  snapshot: GameSnapshot;
  /** When true, shows notification groups from uiStore instead of raw events. */
  grouped?: boolean;
}

/** Color mapping for event types. */
const EVENT_COLORS: Record<string, string> = {
  EXTRACTION: "text-crimson",
  IMPERIAL_RENT: "text-crimson",
  WAGES_PAID: "text-data-green",
  VALUE_TRANSFER: "text-gold",
  CONSCIOUSNESS_SHIFT: "text-gold",
  SOLIDARITY_FORMED: "text-royal-blue",
  SOLIDARITY_BROKEN: "text-phosphor-red",
  BIFURCATION: "text-warning-amber",
  UPRISING: "text-crimson",
  EXCESSIVE_FORCE: "text-phosphor-red",
  RUPTURE: "text-crimson",
  EVICTION: "text-phosphor-red",
  HEAT_SPIKE: "text-warning-amber",
  ORG_FORMED: "text-grow-purple",
  ORG_DISSOLVED: "text-ash",
  ACTION_RESULT: "text-royal-blue",
  FACTION_SHIFT: "text-silver",
  BONAPARTIST_MODE: "text-gold",
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

const SEVERITY_COLORS: Record<string, string> = {
  critical: "border-l-crimson bg-crimson/5",
  important: "border-l-warning-amber bg-warning-amber/5",
  informational: "border-l-soot",
};

export function EventLog({ snapshot, grouped = false }: EventLogProps) {
  const tickSummaries = useGameStore((s) => s.tickSummaries);
  const notificationGroups = useUIStore((s) => s.notificationGroupsForTick);
  const notifications = useUIStore((s) => s.notifications);
  const markAllEventsRead = useUIStore((s) => s.markAllEventsRead);
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [snapshot.events.length, tickSummaries.length, notifications.length]);

  // Grouped notification mode
  if (grouped) {
    const unread = notifications.filter((e) => !e.read).length;
    return (
      <div className="flex h-full flex-col overflow-hidden">
        {unread > 0 && (
          <div className="flex shrink-0 items-center justify-between border-b border-soot px-2 py-1">
            <span className="text-[10px] text-ash">{unread} unread</span>
            <button
              onClick={markAllEventsRead}
              className="text-[10px] text-gold transition-colors hover:text-bone"
            >
              Mark all read
            </button>
          </div>
        )}
        <div ref={scrollRef} className="flex-1 overflow-auto">
          {notificationGroups.length === 0 && (
            <div className="flex h-full items-center justify-center text-sm text-ash">
              No notifications this tick
            </div>
          )}
          {notificationGroups.map((group, i) => (
            <NotificationGroupRow
              key={`${group.eventType}-${group.severity}-${i}`}
              group={group}
              onNavigate={(type, id) => {
                if (type === "territory") setSelectedHex(id);
                else setSelectedNode(id);
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  // Raw event feed mode
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

function NotificationGroupRow({
  group,
  onNavigate,
}: {
  group: NotificationGroup;
  onNavigate: (type: string, id: string) => void;
}) {
  const severityClass = SEVERITY_COLORS[group.severity] ?? "";
  const rep = group.representativeEvent;
  const hasLink = rep.linkedEntityId && rep.linkedEntityType;

  return (
    <div className={`flex items-center justify-between border-l-2 px-2 py-1.5 ${severityClass}`}>
      <div className="flex flex-col gap-0.5">
        <span className="text-[11px] font-semibold text-bone">{group.summary}</span>
        {group.count > 1 && (
          <span className="text-[9px] text-ash">{group.count} events grouped</span>
        )}
      </div>
      {hasLink && (
        <button
          onClick={() => onNavigate(rep.linkedEntityType as string, rep.linkedEntityId as string)}
          className="rounded px-2 py-0.5 text-[9px] text-gold transition-colors hover:bg-soot"
        >
          View
        </button>
      )}
    </div>
  );
}

function EventRow({ event }: { event: GameEvent }) {
  const color = EVENT_COLORS[event.type] ?? "text-ash";
  const icon = EVENT_ICONS[event.type] ?? "--";
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

function formatEventMessage(event: GameEvent): string {
  const d = event.data;
  const parts: string[] = [];

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
