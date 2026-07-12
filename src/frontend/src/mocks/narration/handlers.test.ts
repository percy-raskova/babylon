/**
 * Tests for the narration mock handlers/fixtures — exercised through the
 * real `fetchNarration` client (the same contract a live backend would
 * satisfy), not by re-implementing MSW assertions here.
 */

import { describe, it, expect, afterEach } from "vitest";
import { server } from "@/test/server";
import { fetchNarration } from "@/lib/narration/client";
import {
  narrationHandlers,
  setSimulatedNarrationStatus,
  resetSimulatedNarrationStatus,
} from "./handlers";
import { NARRATION_FIXTURE_BEATS } from "./fixtures";

describe("narrationHandlers + fixtures", () => {
  afterEach(() => {
    resetSimulatedNarrationStatus();
  });

  it("serves the full fixture set as ready when no since_tick is given", async () => {
    server.use(...narrationHandlers);

    const result = await fetchNarration("g1");

    expect(result.status).toBe("ready");
    expect(result.beats).toHaveLength(NARRATION_FIXTURE_BEATS.length);
    expect(result.beats.map((b) => b.id)).toEqual(NARRATION_FIXTURE_BEATS.map((b) => b.id));
  });

  it("filters to only beats strictly after since_tick", async () => {
    server.use(...narrationHandlers);

    const result = await fetchNarration("g1", 104);

    expect(result.beats.every((b) => b.tick > 104)).toBe(true);
    expect(result.beats.length).toBeGreaterThan(0);
    expect(result.beats.length).toBeLessThan(NARRATION_FIXTURE_BEATS.length);
  });

  it("every fixture beat is grounded in the tick-104/Wayne-County exemplar (mentions tick and register-appropriate voice)", () => {
    for (const beat of NARRATION_FIXTURE_BEATS) {
      expect(beat.tick).toBeGreaterThan(0);
      expect(["event", "tick", "county", "endgame"]).toContain(beat.scope);
      expect(["wire", "analysis"]).toContain(beat.register);
      expect(beat.headline.length).toBeGreaterThan(0);
      expect(beat.body.length).toBeGreaterThan(0);
      // No ALL-CAPS shouting (Design Bible §6).
      expect(beat.headline).not.toEqual(beat.headline.toUpperCase());
    }
  });

  it("has at least one beat per scope (event/tick/county/endgame)", () => {
    const scopes = new Set(NARRATION_FIXTURE_BEATS.map((b) => b.scope));
    expect(scopes).toEqual(new Set(["event", "tick", "county", "endgame"]));
  });

  it("has beats in both voice registers (wire and analysis)", () => {
    const registers = new Set(NARRATION_FIXTURE_BEATS.map((b) => b.register));
    expect(registers).toEqual(new Set(["wire", "analysis"]));
  });

  it("setSimulatedNarrationStatus lets a test simulate offline/pending without touching beats", async () => {
    server.use(...narrationHandlers);
    setSimulatedNarrationStatus("pending");

    const result = await fetchNarration("g1");

    expect(result).toEqual({ status: "pending", beats: [] });
  });
});
