/**
 * Tests for eventClassifier — severity mapping against the engine's
 * lowercase `EventType` StrEnum values (src/babylon/models/enums/events.py).
 *
 * The engine publishes events with `event.type` set to the lowercase StrEnum
 * *value* (e.g. "rupture", not "RUPTURE"). The severity map must key on
 * those lowercase values or every lookup falls through to "informational".
 */

import { describe, it, expect } from "vitest";
import { classifyEvent, classifyEventForStream } from "@/lib/eventClassifier";
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

describe("classifyEvent — severity map keyed on lowercase EventType values", () => {
  it("classifies a 'rupture' event as critical", () => {
    const ce = classifyEvent(makeEvent("rupture"), 0);
    expect(ce.severity).toBe("critical");
  });

  it("classifies an 'uprising' event as important", () => {
    const ce = classifyEvent(makeEvent("uprising"), 0);
    expect(ce.severity).toBe("important");
  });

  it("classifies an unknown event type as informational", () => {
    const ce = classifyEvent(makeEvent("totally_unknown_type"), 0);
    expect(ce.severity).toBe("informational");
  });

  it("classifies 'excessive_force' as important", () => {
    const ce = classifyEvent(makeEvent("excessive_force"), 0);
    expect(ce.severity).toBe("important");
  });

  it("classifies 'value_transfer' as informational", () => {
    const ce = classifyEvent(makeEvent("value_transfer"), 0);
    expect(ce.severity).toBe("informational");
  });

  it("classifies 'consciousness_shift' as informational", () => {
    const ce = classifyEvent(makeEvent("consciousness_shift"), 0);
    expect(ce.severity).toBe("informational");
  });

  it("classifies 'surplus_extraction' as informational (replaces dead EXTRACTION key)", () => {
    const ce = classifyEvent(makeEvent("surplus_extraction"), 0);
    expect(ce.severity).toBe("informational");
  });

  it("classifies 'bifurcation_threshold' as important (replaces dead BIFURCATION key)", () => {
    const ce = classifyEvent(makeEvent("bifurcation_threshold"), 0);
    expect(ce.severity).toBe("important");
  });

  it("classifies 'bifurcation_tendency_change' as important", () => {
    const ce = classifyEvent(makeEvent("bifurcation_tendency_change"), 0);
    expect(ce.severity).toBe("important");
  });

  it("classifies 'solidarity_awakening' as important (replaces dead SOLIDARITY_FORMED key)", () => {
    const ce = classifyEvent(makeEvent("solidarity_awakening"), 0);
    expect(ce.severity).toBe("important");
  });

  it("classifies 'solidarity_spike' as important (replaces dead SOLIDARITY_BROKEN key)", () => {
    const ce = classifyEvent(makeEvent("solidarity_spike"), 0);
    expect(ce.severity).toBe("important");
  });

  // 'eviction' is a DispossessionType (legal.py), NOT an EventType. The engine
  // never emits event.type === "eviction"; eviction data surfaces via
  // dispossession_event/ value_transfer events. The old UPPERCASE special-case
  // (event.type === "EVICTION") was dead code — it could never match a real
  // engine event. After the fix there is no special-case: an "eviction" type
  // falls through to the default, classifying as informational.
  it("classifies an 'eviction' type as informational (not an EventType; no special-case)", () => {
    const ce = classifyEvent(makeEvent("eviction"), 0);
    expect(ce.severity).toBe("informational");
  });
});

describe("classifyEventForStream — the two-stream toast/tray model (spec-113 §5.2)", () => {
  it("maps critical severity to the urgent stream and 'critical' tier", () => {
    const se = classifyEventForStream(makeEvent("rupture"), 0);
    expect(se.severity).toBe("critical");
    expect(se.stream).toBe("urgent");
    expect(se.category).toBe("struggle");
  });

  it("maps important severity to the urgent stream and 'notable' tier", () => {
    const se = classifyEventForStream(makeEvent("uprising"), 0);
    expect(se.severity).toBe("notable");
    expect(se.stream).toBe("urgent");
  });

  it("maps informational severity to the ambient stream and 'ambient' tier", () => {
    const se = classifyEventForStream(makeEvent("value_transfer"), 0);
    expect(se.severity).toBe("ambient");
    expect(se.stream).toBe("ambient");
    expect(se.category).toBe("economy");
  });

  it("elevates a genuinely unknown type to 'notable' rather than burying it as ambient", () => {
    const se = classifyEventForStream(makeEvent("totally_unknown_type"), 0);
    expect(se.severity).toBe("notable");
    expect(se.stream).toBe("urgent");
    expect(se.category).toBe("system");
    // The raw type stays visible on the event — never dropped.
    expect(se.event.type).toBe("totally_unknown_type");
  });

  it("classifies a solidarity-family event into the solidarity category", () => {
    const se = classifyEventForStream(makeEvent("solidarity_awakening"), 0);
    expect(se.category).toBe("solidarity");
  });

  it("classifies a political-family event (sovereign_collapse) as critical/urgent/political", () => {
    const se = classifyEventForStream(makeEvent("sovereign_collapse"), 0);
    expect(se.severity).toBe("critical");
    expect(se.stream).toBe("urgent");
    expect(se.category).toBe("political");
  });
});
