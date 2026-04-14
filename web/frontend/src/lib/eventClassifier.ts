/**
 * Event classifier — maps engine EventTypes to UI severity tiers.
 *
 * Per research.md R-002: severity is a presentation concern, not a simulation
 * concern. This static mapping enables frontend classification without
 * coupling to the engine.
 */

import type { GameEvent, ClassifiedEvent, EventSeverity } from "@/types/game";

/** Static mapping from event type to default severity. */
const EVENT_SEVERITY_MAP: Record<string, EventSeverity> = {
  // Critical — existential state changes and terminal endgame
  RUPTURE: "critical",
  REVOLUTIONARY_VICTORY: "critical",
  ECOLOGICAL_COLLAPSE: "critical",
  FASCIST_CONSOLIDATION: "critical",

  // Important — phase transitions and strategic shifts
  BIFURCATION: "important",
  SOLIDARITY_FORMED: "important",
  SOLIDARITY_BROKEN: "important",
  EXCESSIVE_FORCE: "important",
  UPRISING: "important",

  // Informational — gradual changes and background flow
  EVICTION: "informational",
  VALUE_TRANSFER: "informational",
  CONSCIOUSNESS_SHIFT: "informational",
  HEAT_CHANGE: "informational",
  EXTRACTION: "informational",
};

/**
 * Determine if an eviction affects a player-controlled territory.
 * Evictions in player territories are critical; others are informational.
 */
function getEvictionSeverity(event: GameEvent, playerOrgIds: ReadonlySet<string>): EventSeverity {
  const targetOrgId = event.data?.org_id as string | undefined;
  if (targetOrgId && playerOrgIds.has(targetOrgId)) {
    return "critical";
  }
  return "informational";
}

/**
 * Extract a linked entity reference from an event for navigation.
 */
function extractLinkedEntity(event: GameEvent): {
  linkedEntityId: string | null;
  linkedEntityType: ClassifiedEvent["linkedEntityType"];
} {
  const data = event.data;
  if (data?.territory_id) {
    return { linkedEntityId: data.territory_id as string, linkedEntityType: "territory" };
  }
  if (data?.org_id) {
    return { linkedEntityId: data.org_id as string, linkedEntityType: "organization" };
  }
  if (data?.entity_id || data?.source_id) {
    return {
      linkedEntityId: (data.entity_id ?? data.source_id) as string,
      linkedEntityType: "organization",
    };
  }
  return { linkedEntityId: null, linkedEntityType: null };
}

/**
 * Classify a single game event into a ClassifiedEvent with severity and
 * navigation metadata.
 *
 * @param event - Raw engine event
 * @param index - Index within the tick's event array (for unique ID generation)
 * @param playerOrgIds - Set of organization IDs the player controls (for
 *   context-sensitive severity, e.g. evictions)
 */
export function classifyEvent(
  event: GameEvent,
  index: number,
  playerOrgIds: ReadonlySet<string> = new Set(),
): ClassifiedEvent {
  let severity: EventSeverity;

  if (event.type === "EVICTION") {
    severity = getEvictionSeverity(event, playerOrgIds);
  } else {
    severity = EVENT_SEVERITY_MAP[event.type] ?? "informational";
  }

  const { linkedEntityId, linkedEntityType } = extractLinkedEntity(event);

  return {
    id: `${event.tick}-${index}`,
    event,
    severity,
    tick: event.tick,
    read: false,
    linkedEntityId,
    linkedEntityType,
  };
}

/**
 * Classify an array of events from a single tick.
 */
export function classifyEvents(
  events: GameEvent[],
  playerOrgIds: ReadonlySet<string> = new Set(),
): ClassifiedEvent[] {
  return events.map((event, index) => classifyEvent(event, index, playerOrgIds));
}
