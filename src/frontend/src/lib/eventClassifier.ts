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
 *
 * spec-113 Lane E: extended coverage to the rest of the 79-value EventType
 * enum (`src/babylon/models/enums/events.py`) so `classifyEvent`'s default
 * fallback ("informational") stops being the accidental answer for most of
 * the engine's real event vocabulary. The originally-tested nine keys above
 * keep their exact values — this only adds new keys.
 */
const EVENT_SEVERITY_MAP: Record<string, EventSeverity> = {
  // Critical — existential state changes
  rupture: "critical",
  terminal_decision: "critical",
  control_ratio_crisis: "critical",
  civil_war_declared: "critical",
  red_brown_coup: "critical",
  sovereign_collapse: "critical",
  red_ogv_endgame: "critical",
  fragmented_collapse_endgame: "critical",
  endgame_reached: "critical",

  // Important — phase transitions and strategic shifts
  bifurcation_threshold: "important",
  bifurcation_tendency_change: "important",
  solidarity_awakening: "important",
  solidarity_spike: "important",
  excessive_force: "important",
  uprising: "important",
  power_vacuum: "important",
  revolutionary_offensive: "important",
  fascist_revanchism: "important",
  phase_transition: "important",
  peripheral_revolt: "important",
  superwage_crisis: "important",
  class_decomposition: "important",
  economic_crisis: "important",
  ecological_overshoot: "important",
  territory_transition: "important",
  faction_victory: "important",
  secession_declared: "important",
  red_settler_trap_detected: "important",
  dual_power_active: "important",
  fascist_drift: "important",
  fascist_recruitment: "important",
  organizational_fracture: "important",
  pogrom: "important",
  lockout: "important",
  vigilantism: "important",
  spontaneous_riot: "important",
  fascist_convergence: "important",
  legitimation_crisis: "important",
  crisis_phase_transition: "important",
  dispossession_cascade: "important",
  co_optive_breakdown: "important",
  latent_contradiction_release: "important",
  state_repression: "important",

  // Informational — gradual changes and background flow
  value_transfer: "informational",
  consciousness_shift: "informational",
  surplus_extraction: "informational",
  imperial_subsidy: "informational",
  consciousness_transmission: "informational",
  mass_awakening: "informational",
  entity_death: "informational",
  population_death: "informational",
  population_attrition: "informational",
  edge_mode_transition: "informational",
  principal_contradiction_shift: "informational",
  level_transition: "informational",
  aspect_reversal: "informational",
  reserve_army_pressure: "informational",
  dispossession_event: "informational",
  exploitation_mode_shift: "informational",
  lifecycle_transition: "informational",
  legitimation_recovery: "informational",
  inheritance_transfer: "informational",
  dual_circuit_interference: "informational",
  organizational_action: "informational",
  state_surveillance: "informational",
  initiative_contested: "informational",
  infrastructure_change: "informational",
  calibration_disagreement: "informational",
  state_action_executed: "informational",
  faction_shift: "informational",
  thread_escalation: "informational",
  legal_framework_enacted: "informational",
  legal_framework_revoked: "informational",
  institution_faction_shift: "informational",
  institution_reproduction: "informational",
  institution_bonapartist_mode: "informational",
  "calibration_warning.axiom_violation": "informational",
  "calibration_warning.qcew_carry_forward": "informational",
  "calibration_warning.phi_hour_outlier": "informational",
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

// ---------------------------------------------------------------------------
// spec-113 Lane E — stream classification (DESIGN_BIBLE §5.2): a second,
// independent classification consumed only by `eventsSlice` (toasts/tray/
// mutes). Kept separate from `classifyEvent`/`ClassifiedEvent` above (an
// existing, tested contract other lanes' components already read) rather
// than repurposing it, so this extension can use the bible's own vocabulary
// (ambient/notable/critical severities, urgent/ambient streams, categories)
// without changing the meaning of any existing call site.
// ---------------------------------------------------------------------------

/** Severity vocabulary for the toast/tray layer (DESIGN_BIBLE §5.2). */
export type StreamSeverity = "ambient" | "notable" | "critical";

/** Which of the two event streams (DESIGN_BIBLE §5.2) an event belongs to. */
export type EventStream = "urgent" | "ambient";

/** Coarse thematic grouping, driving per-category mute (DESIGN_BIBLE §5.2). */
export type EventCategory =
  "struggle" | "solidarity" | "economy" | "political" | "ecology" | "population" | "system";

/** Every `EventCategory`, in a stable display order — for mute-toggle UI. */
export const EVENT_CATEGORIES: readonly EventCategory[] = [
  "struggle",
  "solidarity",
  "economy",
  "political",
  "ecology",
  "population",
  "system",
];

/** A classified event annotated for the two-stream toast/tray model. */
export interface StreamEvent {
  id: string;
  event: GameEvent;
  tick: number;
  severity: StreamSeverity;
  category: EventCategory;
  stream: EventStream;
  linkedEntityId: string | null;
  linkedEntityType: ClassifiedEvent["linkedEntityType"];
}

const CATEGORY_MAP: Record<string, EventCategory> = {
  // struggle — direct class conflict / repression / rupture dynamics
  rupture: "struggle",
  uprising: "struggle",
  excessive_force: "struggle",
  spontaneous_riot: "struggle",
  pogrom: "struggle",
  lockout: "struggle",
  vigilantism: "struggle",
  red_brown_coup: "struggle",
  organizational_fracture: "struggle",
  control_ratio_crisis: "struggle",
  terminal_decision: "struggle",
  civil_war_declared: "struggle",
  peripheral_revolt: "struggle",
  class_decomposition: "struggle",
  power_vacuum: "struggle",
  revolutionary_offensive: "struggle",
  fascist_revanchism: "struggle",
  co_optive_breakdown: "struggle",
  latent_contradiction_release: "struggle",
  state_repression: "struggle",
  initiative_contested: "struggle",

  // solidarity — consciousness / organizing gains
  solidarity_awakening: "solidarity",
  solidarity_spike: "solidarity",
  consciousness_transmission: "solidarity",
  mass_awakening: "solidarity",
  consciousness_shift: "solidarity",
  dual_power_active: "solidarity",

  // economy — value flows, extraction, dispossession
  surplus_extraction: "economy",
  imperial_subsidy: "economy",
  economic_crisis: "economy",
  superwage_crisis: "economy",
  dispossession_event: "economy",
  dispossession_cascade: "economy",
  value_transfer: "economy",
  reserve_army_pressure: "economy",
  exploitation_mode_shift: "economy",
  calibration_disagreement: "economy",
  "calibration_warning.axiom_violation": "economy",
  "calibration_warning.qcew_carry_forward": "economy",
  "calibration_warning.phi_hour_outlier": "economy",

  // political — sovereignty, factions, institutions, legal apparatus
  sovereign_collapse: "political",
  territory_transition: "political",
  faction_victory: "political",
  secession_declared: "political",
  red_settler_trap_detected: "political",
  red_ogv_endgame: "political",
  fragmented_collapse_endgame: "political",
  faction_shift: "political",
  institution_faction_shift: "political",
  legal_framework_enacted: "political",
  legal_framework_revoked: "political",
  state_action_executed: "political",
  organizational_action: "political",
  state_surveillance: "political",
  thread_escalation: "political",
  fascist_convergence: "political",
  fascist_drift: "political",
  fascist_recruitment: "political",
  institution_reproduction: "political",
  institution_bonapartist_mode: "political",

  // ecology — metabolic rift
  ecological_overshoot: "ecology",

  // population — lifecycle, mortality, legitimation
  entity_death: "population",
  population_death: "population",
  population_attrition: "population",
  lifecycle_transition: "population",
  legitimation_crisis: "population",
  legitimation_recovery: "population",
  inheritance_transfer: "population",
  dual_circuit_interference: "population",

  // system — topology/field mechanics, endgame housekeeping
  phase_transition: "system",
  edge_mode_transition: "system",
  principal_contradiction_shift: "system",
  level_transition: "system",
  aspect_reversal: "system",
  bifurcation_threshold: "system",
  bifurcation_tendency_change: "system",
  crisis_phase_transition: "system",
  infrastructure_change: "system",
  endgame_reached: "system",
};

/** True for entries `EVENT_SEVERITY_MAP` (and by extension `CATEGORY_MAP`) actually defines. */
function isKnownEventType(type: string): boolean {
  return Object.prototype.hasOwnProperty.call(EVENT_SEVERITY_MAP, type);
}

/**
 * Map the existing three-tier `EventSeverity` onto the bible's
 * ambient/notable/critical vocabulary. An event type the map has never seen
 * before is deliberately elevated to "notable" rather than defaulting to
 * "ambient" — an unrecognized event is exactly the case where silently
 * burying it in the low-priority bucket would be dishonest (III.11); the
 * raw `event.type` stays visible on the resulting `StreamEvent` either way.
 */
function toStreamSeverity(event: GameEvent): StreamSeverity {
  if (!isKnownEventType(event.type)) return "notable";
  const severity = EVENT_SEVERITY_MAP[event.type];
  if (severity === "critical") return "critical";
  if (severity === "important") return "notable";
  return "ambient";
}

/**
 * Classify one event for the two-stream toast/tray model (DESIGN_BIBLE
 * §5.2). Unknown types fall into `category: "system"` — never dropped.
 */
export function classifyEventForStream(event: GameEvent, index: number): StreamEvent {
  const { linkedEntityId, linkedEntityType } = extractLinkedEntity(event);
  const severity = toStreamSeverity(event);
  const category = CATEGORY_MAP[event.type] ?? "system";

  return {
    id: `${event.tick}-${index}`,
    event,
    tick: event.tick,
    severity,
    category,
    stream: severity === "ambient" ? "ambient" : "urgent",
    linkedEntityId,
    linkedEntityType,
  };
}

/** Classify an array of events from a single tick for the toast/tray model. */
export function classifyEventsForStream(events: GameEvent[]): StreamEvent[] {
  return events.map((event, index) => classifyEventForStream(event, index));
}
