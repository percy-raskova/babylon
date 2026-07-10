/**
 * Event classifier — maps engine EventTypes to UI severity tiers.
 *
 * Per research.md R-002: severity is a presentation concern, not a simulation
 * concern. This static mapping enables frontend classification without
 * coupling to the engine.
 */

import type { GameEvent, ClassifiedEvent, EventSeverity } from "@/types/game";

/**
 * Static mapping from event type to default severity.
 *
 * Keys are the lowercase StrEnum *values* the engine emits as `event.type`
 * (see `src/babylon/models/enums/events.py` `EventType`). The previous
 * UPPERCASE keys never matched and every lookup fell through to
 * "informational".
 *
 * Removed dead keys (not EventType values — the engine never emits them as
 * `event.type`):
 *   - REVOLUTIONARY_VICTORY / ECOLOGICAL_COLLAPSE / FASCIST_CONSOLIDATION are
 *     `GameOutcome` values, surfaced on the snapshot's endgame state, not as
 *     events.
 *   - EVICTION is a `DispossessionType` (legal.py); eviction data surfaces via
 *     `dispossession_event` / `value_transfer` events.
 *   - HEAT_CHANGE has no EventType counterpart.
 *
 * Replaced approximate keys with the real EventType values:
 *   - BIFURCATION → bifurcation_threshold + bifurcation_tendency_change
 *   - EXTRACTION → surplus_extraction
 *   - SOLIDARITY_FORMED / SOLIDARITY_BROKEN → solidarity_awakening +
 *     solidarity_spike
 */
const EVENT_SEVERITY_MAP: Record<string, EventSeverity> = {
  // Critical — existential state changes
  rupture: "critical",

  // Important — phase transitions and strategic shifts
  bifurcation_threshold: "important",
  bifurcation_tendency_change: "important",
  solidarity_awakening: "important",
  solidarity_spike: "important",
  excessive_force: "important",
  uprising: "important",

  // Informational — gradual changes and background flow
  value_transfer: "informational",
  consciousness_shift: "informational",
  surplus_extraction: "informational",
};

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
 */
export function classifyEvent(event: GameEvent, index: number): ClassifiedEvent {
  const severity: EventSeverity = EVENT_SEVERITY_MAP[event.type] ?? "informational";

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
export function classifyEvents(events: GameEvent[]): ClassifiedEvent[] {
  return events.map((event, index) => classifyEvent(event, index));
}
