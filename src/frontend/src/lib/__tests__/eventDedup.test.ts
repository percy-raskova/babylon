/**
 * Tests for eventDedup (spec-116 FR-116-2) — tick-independent salience
 * identity, consecutive-run collapse, and the autopause-once core.
 *
 * The property-style suites use a seeded deterministic PRNG (mulberry32)
 * with FIXED iteration bounds (Power-of-10 rule 2: every loop statically
 * bounded) rather than a hypothesis-style framework; the failing seed is
 * carried in each assertion message.
 */

import { describe, it, expect } from "vitest";
import {
  ALWAYS_AUTOPAUSE_TYPES,
  computeAutopauseDecision,
  dedupKey,
  dedupeEvents,
  eventSubject,
} from "@/lib/eventDedup";
import { classifyEvents } from "@/lib/eventClassifier";
import type { GameEvent } from "@/types/game";

function makeEvent(type: string, overrides: Partial<GameEvent> = {}): GameEvent {
  return {
    id: "test-event",
    type,
    tick: 1,
    severity: "informational",
    title: "Test",
    body: "",
    data: {},
    ...overrides,
  };
}

describe("eventSubject / dedupKey — tick-independent salience identity", () => {
  it("prefers node_id over the bridge-enriched territory_id (graph-independence)", () => {
    const e = makeEvent("uprising", { data: { node_id: "class-42", territory_id: "26163" } });
    expect(eventSubject(e)).toBe("class-42");
    expect(dedupKey(e)).toBe("uprising:class-42");
  });

  it("keys org events on org_id", () => {
    const e = makeEvent("state_repression", { data: { org_id: "org-maga" } });
    expect(dedupKey(e)).toBe("state_repression:org-maga");
  });

  it("stringifies numeric subjects (fips)", () => {
    const e = makeEvent("dispossession_cascade", { data: { fips: 26163 } });
    expect(dedupKey(e)).toBe("dispossession_cascade:26163");
  });

  it("falls back to source->target for flow events", () => {
    const e = makeEvent("surplus_extraction", {
      data: { source_id: "periphery-1", target_id: "core-1" },
    });
    expect(dedupKey(e)).toBe("surplus_extraction:periphery-1->core-1");
  });

  it("falls back to 'global' when no subject field is present", () => {
    expect(dedupKey(makeEvent("endgame_reached", { data: { outcome: "red_ogv" } }))).toBe(
      "endgame_reached:global",
    );
  });

  it("is tick-independent: the same (type,subject) on different ticks yields the same key", () => {
    const a = makeEvent("uprising", { tick: 3, data: { node_id: "n1" } });
    const b = makeEvent("uprising", { tick: 9, data: { node_id: "n1" } });
    expect(dedupKey(a)).toBe(dedupKey(b));
  });
});

describe("dedupeEvents — consecutive same-(type,subject) collapse", () => {
  it("collapses a consecutive same-key run into one card with count and first/last tick", () => {
    const cards = dedupeEvents(
      classifyEvents([
        makeEvent("dispossession_event", { tick: 4, data: { territory: "26163" } }),
        makeEvent("dispossession_event", { tick: 4, data: { territory: "26163" } }),
        makeEvent("dispossession_event", { tick: 4, data: { territory: "26163" } }),
      ]),
    );
    expect(cards).toHaveLength(1);
    expect(cards[0]).toMatchObject({
      key: "dispossession_event:26163",
      count: 3,
      firstTick: 4,
      lastTick: 4,
    });
    expect(cards[0]!.representative.id).toBe("4-0");
  });

  it("does NOT collapse the same type with different subjects", () => {
    const cards = dedupeEvents(
      classifyEvents([
        makeEvent("dispossession_event", { tick: 4, data: { territory: "26163" } }),
        makeEvent("dispossession_event", { tick: 4, data: { territory: "26099" } }),
      ]),
    );
    expect(cards).toHaveLength(2);
  });

  it("does NOT collapse a non-consecutive repeat (A B A stays three cards)", () => {
    const cards = dedupeEvents(
      classifyEvents([
        makeEvent("uprising", { tick: 4, data: { node_id: "n1" } }),
        makeEvent("state_repression", { tick: 4, data: { org_id: "o1" } }),
        makeEvent("uprising", { tick: 4, data: { node_id: "n1" } }),
      ]),
    );
    expect(cards.map((c) => c.key)).toEqual(["uprising:n1", "state_repression:o1", "uprising:n1"]);
  });
});

describe("computeAutopauseDecision — the autopause-once core", () => {
  const acked = (...keys: string[]): ReadonlySet<string> => new Set(keys);

  it("declares endgame_reached an always-autopause type", () => {
    expect(ALWAYS_AUTOPAUSE_TYPES.has("endgame_reached")).toBe(true);
  });

  it("fires each distinct (type,subject) once, deduping same-tick repeats", () => {
    const events = [
      makeEvent("uprising", { tick: 4, data: { node_id: "n1" } }),
      makeEvent("uprising", { tick: 4, data: { node_id: "n1" } }),
      makeEvent("uprising", { tick: 4, data: { node_id: "n2" } }),
    ];
    const d = computeAutopauseDecision(events, acked());
    expect(d.firingKeys).toEqual(["uprising:n1", "uprising:n2"]);
    expect(d.acknowledgementKeys).toEqual(["uprising:n1", "uprising:n2"]);
  });

  it("suppresses a key that already fired this session", () => {
    const events = [makeEvent("uprising", { tick: 9, data: { node_id: "n1" } })];
    const d = computeAutopauseDecision(events, acked("uprising:n1"));
    expect(d.firingKeys).toEqual([]);
    expect(d.acknowledgementKeys).toEqual([]);
  });

  it("endgame_reached fires per occurrence: same tick suppressed (load race), new tick fires", () => {
    const endgame = makeEvent("endgame_reached", { tick: 52, data: { outcome: "red_ogv" } });
    const first = computeAutopauseDecision([endgame], acked());
    expect(first.firingKeys).toEqual(["endgame_reached:global"]);
    expect(first.acknowledgementKeys).toEqual(["endgame_reached:global@52"]);

    const raced = computeAutopauseDecision([endgame], acked("endgame_reached:global@52"));
    expect(raced.firingKeys).toEqual([]);

    const later = makeEvent("endgame_reached", { tick: 53, data: { outcome: "red_ogv" } });
    const again = computeAutopauseDecision([later], acked("endgame_reached:global@52"));
    expect(again.firingKeys).toEqual(["endgame_reached:global"]);
    expect(again.acknowledgementKeys).toEqual(["endgame_reached:global@53"]);
  });
});

// ---------------------------------------------------------------------------
// Property-style suites — seeded PRNG, fixed bounds.
// ---------------------------------------------------------------------------

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const GEN_TYPES = ["uprising", "state_repression", "endgame_reached"] as const;
const GEN_SUBJECTS: readonly Record<string, unknown>[] = [
  { node_id: "n1" },
  { node_id: "n2" },
  { org_id: "o1" },
  {},
];

function randomEvents(rand: () => number, count: number, tick: number): GameEvent[] {
  const out: GameEvent[] = [];
  for (let i = 0; i < count; i++) {
    const type = GEN_TYPES[Math.floor(rand() * GEN_TYPES.length)]!;
    const data = GEN_SUBJECTS[Math.floor(rand() * GEN_SUBJECTS.length)]!;
    out.push(makeEvent(type, { tick, data: { ...data } }));
  }
  return out;
}

describe("salience properties (seeded, fixed bounds)", () => {
  const CASES = 100;
  const MAX_EVENTS = 30;
  const MAX_TICKS = 12;

  it("dedupeEvents partitions its input in order with no adjacent equal keys", () => {
    for (let c = 0; c < CASES; c++) {
      const rand = mulberry32(c + 1);
      const n = 1 + Math.floor(rand() * MAX_EVENTS);
      const items = classifyEvents(randomEvents(rand, n, 7));
      const runs = dedupeEvents(items);

      const total = runs.reduce((sum, r) => sum + r.count, 0);
      expect(total, `seed ${c + 1}: counts must sum to input length`).toBe(items.length);
      expect(
        runs.flatMap((r) => r.events),
        `seed ${c + 1}: flattened runs must reproduce the input in order`,
      ).toEqual(items);
      for (let i = 1; i < runs.length; i++) {
        expect(
          runs[i]!.key,
          `seed ${c + 1}: adjacent runs ${i - 1},${i} must differ (acceptance gate 2)`,
        ).not.toBe(runs[i - 1]!.key);
      }
      for (const r of runs) {
        expect(
          r.events.every((e) => dedupKey(e.event) === r.key),
          `seed ${c + 1}: every member of a run shares its key`,
        ).toBe(true);
      }
    }
  });

  it("dedupeEvents is idempotent on collapsed representatives", () => {
    for (let c = 0; c < CASES; c++) {
      const seed = 1000 + c;
      const rand = mulberry32(seed);
      const n = 1 + Math.floor(rand() * MAX_EVENTS);
      const runs = dedupeEvents(classifyEvents(randomEvents(rand, n, 3)));
      const again = dedupeEvents(runs.map((r) => r.representative));
      expect(
        again.map((r) => r.key),
        `seed ${seed}: re-collapsing must preserve the key sequence`,
      ).toEqual(runs.map((r) => r.key));
      expect(
        again.every((r) => r.count === 1),
        `seed ${seed}: an already-collapsed sequence has nothing left to merge`,
      ).toBe(true);
    }
  });

  it("autopause-once: a non-ALWAYS key fires at most once across any tick sequence", () => {
    for (let c = 0; c < CASES; c++) {
      const seed = 2000 + c;
      const rand = mulberry32(seed);
      const acknowledged = new Set<string>();
      const firedPerKey = new Map<string, number>();
      const ticks = 1 + Math.floor(rand() * MAX_TICKS);
      for (let tick = 1; tick <= ticks; tick++) {
        const n = Math.floor(rand() * 6);
        const decision = computeAutopauseDecision(randomEvents(rand, n, tick), acknowledged);
        for (const key of decision.acknowledgementKeys) acknowledged.add(key);
        for (const key of decision.firingKeys) {
          firedPerKey.set(key, (firedPerKey.get(key) ?? 0) + 1);
        }
      }
      for (const [key, fired] of firedPerKey) {
        if (!key.startsWith("endgame_reached:")) {
          expect(fired, `seed ${seed}: key ${key} fired ${fired}×`).toBeLessThanOrEqual(1);
        }
      }
    }
  });
});
