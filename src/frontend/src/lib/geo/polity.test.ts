/**
 * lib/geo/polity.test.ts — shared-arc dissolve correctness + memoization contract
 * (spec-113 §7 task 2). Fixture: `__fixtures__/mini-counties.topojson.json`, a
 * hand-authored 2x2 grid of unit-square counties run through the real mapshaper
 * pipeline (see `__fixtures__/README.md` for the adjacency layout).
 */

import { beforeEach, describe, expect, it } from "vitest";
import { mergePolity, mergePolityOutline, resetPolityCache } from "./polity";
import type { CountyTopology } from "./topology";
import miniCounties from "./__fixtures__/mini-counties.topojson.json";

const topo = miniCounties as unknown as CountyTopology;

beforeEach(() => {
  resetPolityCache();
});

describe("mergePolity", () => {
  it("dissolves two edge-adjacent counties into a single ring (no interior seam)", () => {
    // 00001 (Alpha) and 00002 (Beta) share a vertical edge.
    const merged = mergePolity(topo, ["00001", "00002"]);
    expect(merged.type).toBe("MultiPolygon");
    expect(merged.coordinates).toHaveLength(1); // one polygon
    expect(merged.coordinates[0]).toHaveLength(1); // one ring — no hole/seam
  });

  it("keeps two non-adjacent (diagonal) counties as two separate rings", () => {
    // 00001 (Alpha) and 00004 (Delta) share only a corner point, not an edge.
    const merged = mergePolity(topo, ["00001", "00004"]);
    expect(merged.type).toBe("MultiPolygon");
    expect(merged.coordinates).toHaveLength(2);
  });

  it("dissolves all four counties (full grid) into a single outer ring", () => {
    const merged = mergePolity(topo, ["00001", "00002", "00003", "00004"]);
    expect(merged.coordinates).toHaveLength(1);
    expect(merged.coordinates[0]).toHaveLength(1);
  });

  it("memoizes by sorted FIPS membership — repeat calls return the identical reference", () => {
    const a = mergePolity(topo, ["00001", "00002"]);
    const b = mergePolity(topo, ["00001", "00002"]);
    expect(b).toBe(a);
  });

  it("memoization is order-independent", () => {
    const a = mergePolity(topo, ["00001", "00002"]);
    const b = mergePolity(topo, ["00002", "00001"]);
    expect(b).toBe(a);
  });

  it("memoization is de-duplication-safe (repeated FIPS in the input list)", () => {
    const a = mergePolity(topo, ["00001", "00002"]);
    const b = mergePolity(topo, ["00001", "00001", "00002"]);
    expect(b).toBe(a);
  });

  it("returns a distinct reference for a different membership", () => {
    const a = mergePolity(topo, ["00001", "00002"]);
    const b = mergePolity(topo, ["00003", "00004"]);
    expect(b).not.toBe(a);
  });
});

describe("mergePolityOutline", () => {
  it("produces a single exterior ring for two adjacent counties (no interior seam)", () => {
    const outline = mergePolityOutline(topo, ["00001", "00002"]);
    expect(outline.type).toBe("MultiLineString");
    expect(outline.coordinates).toHaveLength(1);
  });

  it("memoizes identically to mergePolity", () => {
    const a = mergePolityOutline(topo, ["00001", "00002"]);
    const b = mergePolityOutline(topo, ["00001", "00002"]);
    expect(b).toBe(a);
  });
});

describe("resetPolityCache", () => {
  it("clears memoized references so a subsequent call produces a fresh object", () => {
    const a = mergePolity(topo, ["00001", "00002"]);
    resetPolityCache();
    const b = mergePolity(topo, ["00001", "00002"]);
    expect(b).not.toBe(a);
    expect(b).toEqual(a);
  });
});
