/**
 * Contract test: journal + alerts endpoints (spec 092).
 *
 * Pins the response shape both `useJournal` and `useAlerts` rely on:
 * `{status: "ok", data: {events: GameEvent[]}}` and
 * `{status: "ok", data: {alerts: GameEvent[]}}` respectively, where each
 * GameEvent carries the full spec-061 FR-012 shape (id/type/tick/severity/
 * title/body/data). Written red-first per spec-092's TDD requirement —
 * MSW has no handler for either route until `test/handlers.ts` is updated.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse, JournalPayload, AlertsPayload, GameEvent } from "@/types/game";

const GAME_ID = "wayne-county-001";

function assertGameEventShape(event: GameEvent): void {
  expect(typeof event.id).toBe("string");
  expect(typeof event.type).toBe("string");
  expect(typeof event.tick).toBe("number");
  expect(["critical", "warning", "informational"]).toContain(event.severity);
  expect(typeof event.title).toBe("string");
  expect(typeof event.body).toBe("string");
  expect(typeof event.data).toBe("object");
}

describe("journal/alerts contract (spec 092)", () => {
  it("GET /api/games/:id/journal/ returns {events: GameEvent[]}", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/journal/`, { credentials: "include" });
    const body = (await res.json()) as ApiResponse<JournalPayload>;

    expect(body.status).toBe("ok");
    expect(Array.isArray(body.data.events)).toBe(true);
    for (const event of body.data.events) {
      assertGameEventShape(event);
    }
  });

  it("GET /api/games/:id/alerts/ returns {alerts: GameEvent[]}", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/alerts/`, { credentials: "include" });
    const body = (await res.json()) as ApiResponse<AlertsPayload>;

    expect(body.status).toBe("ok");
    expect(Array.isArray(body.data.alerts)).toBe(true);
    for (const alert of body.data.alerts) {
      assertGameEventShape(alert);
      // Alerts are non-informational by construction (spec 092 FR-A1).
      expect(alert.severity).not.toBe("informational");
    }
  });
});
