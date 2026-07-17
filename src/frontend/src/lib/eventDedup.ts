/**
 * Event salience (spec-116 FR-116-2) — tick-independent dedup identity,
 * consecutive-run collapse, and the autopause-once core.
 *
 * Frontend-side by design (interface ledger 2026-07-17): the bridge payload
 * stays a plain per-tick event list, and every id the backend serializes is
 * tick-scoped (the UUID5 seed hashes the tick), so a persisting condition
 * gets a NEW id every tick. The stable identity for "the same thing still
 * happening" is `(event_type, subject)`, derived here from payload fields.
 */

import type { GameEvent } from "@/types/game";

/**
 * Subject-field precedence, graph-independent payload fields FIRST:
 * `uprising` events carry both `node_id` (engine payload) and a
 * bridge-enriched `territory_id` that differs between graph-present and
 * graph-absent serialization paths (`engine_bridge._serialize_event`) —
 * keying on `node_id` keeps the identity stable across both.
 */
const SUBJECT_FIELDS: readonly string[] = [
  "node_id",
  "org_id",
  "entity_id",
  "territory_id",
  "territory",
  "fips",
  "county_fips",
  "sovereign_id",
  "faction_id",
  "comprador_id",
  "periphery_id",
  "core_worker_id",
];

/** Resolve an event's subject: first present subject field, else source->target, else "global". */
export function eventSubject(event: GameEvent): string {
  const data = event.data ?? {};
  for (const field of SUBJECT_FIELDS) {
    const value = data[field];
    if (typeof value === "string" && value !== "") return value;
    if (typeof value === "number") return String(value);
  }
  const source = data["source_id"];
  const target = data["target_id"];
  if (typeof source === "string" && typeof target === "string") return `${source}->${target}`;
  if (typeof source === "string") return source;
  return "global";
}

/** Tick-independent salience identity: `${type}:${subject}`. */
export function dedupKey(event: GameEvent): string {
  return `${event.type}:${eventSubject(event)}`;
}

/** Anything carrying a GameEvent + tick can be run-collapsed (ClassifiedEvent, StreamEvent). */
export interface DedupableItem {
  event: GameEvent;
  tick: number;
}

/** One collapsed run of consecutive same-(type,subject) items. */
export interface DedupedRun<T extends DedupableItem> {
  key: string;
  /** FIRST item of the run — carries the run's id/severity/deep-link. */
  representative: T;
  events: T[];
  count: number;
  firstTick: number;
  lastTick: number;
}

/**
 * Collapse CONSECUTIVE same-(type,subject) items into one card each
 * (FR-116-2 i / acceptance gate 2: "no two consecutive identical event
 * cards"). Order-preserving partition; a non-consecutive repeat stays a
 * separate card. Loop bound: `items.length`.
 */
export function dedupeEvents<T extends DedupableItem>(items: readonly T[]): DedupedRun<T>[] {
  const runs: DedupedRun<T>[] = [];
  for (const item of items) {
    const key = dedupKey(item.event);
    const last = runs[runs.length - 1];
    if (last !== undefined && last.key === key) {
      last.events.push(item);
      last.count += 1;
      last.firstTick = Math.min(last.firstTick, item.tick);
      last.lastTick = Math.max(last.lastTick, item.tick);
    } else {
      runs.push({
        key,
        representative: item,
        events: [item],
        count: 1,
        firstTick: item.tick,
        lastTick: item.tick,
      });
    }
  }
  return runs;
}

/**
 * Event types that autopause on EVERY occurrence — never session-muted by
 * the once-per-key rule (interface ledger: "endgame_reached always
 * autopauses"). They acknowledge per-occurrence (`key@tick`), which still
 * suppresses the same-tick double-fire in the load race.
 */
export const ALWAYS_AUTOPAUSE_TYPES: ReadonlySet<string> = new Set(["endgame_reached"]);

/** What one tick's critical events should do to the pause machinery. */
export interface AutopauseDecision {
  /** Dedup keys to pause on — what `time.autopause` receives and the modal joins on. */
  firingKeys: string[];
  /** Session-memory entries to record — `key` normally, `key@tick` for ALWAYS types. */
  acknowledgementKeys: string[];
}

/**
 * The autopause-once core (FR-116-2 iii). PURE: the caller passes ONLY the
 * tick's critical-severity events plus its acknowledged set, and must add
 * the returned `acknowledgementKeys` to that set when it fires the pause.
 * Loop bound: `criticalEvents.length`.
 */
export function computeAutopauseDecision(
  criticalEvents: readonly GameEvent[],
  acknowledged: ReadonlySet<string>,
): AutopauseDecision {
  const firing = new Set<string>();
  const acks: string[] = [];
  const seen = new Set<string>();
  for (const event of criticalEvents) {
    const key = dedupKey(event);
    const ackKey = ALWAYS_AUTOPAUSE_TYPES.has(event.type) ? `${key}@${event.tick}` : key;
    if (seen.has(ackKey) || acknowledged.has(ackKey)) continue;
    seen.add(ackKey);
    acks.push(ackKey);
    firing.add(key);
  }
  return { firingKeys: [...firing], acknowledgementKeys: acks };
}
