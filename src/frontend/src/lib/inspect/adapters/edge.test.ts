/**
 * `adaptEdge`'s history-splicing behavior (audit Wave 4 straggler, task
 * #76 — the edge-weight history sparkline). Base field-dump behavior
 * (empty payload, generic key/value rows) is covered by
 * `genericEntity.test.ts`; this file covers only the additive `history`
 * argument.
 */

import { describe, it, expect } from "vitest";
import { adaptEdge } from "./edge";
import type { EdgeHistoryPoint } from "@/types/game";

const EDGE_REF = { kind: "edge" as const, id: "C001->C004" };

describe("adaptEdge — history splicing (audit Wave 4 straggler, task #76)", () => {
  it("attaches history to the value_flow row when present", () => {
    const history: EdgeHistoryPoint[] = [
      { tick: 0, weight: 1.0, solidarity: null, tension: 0.1 },
      { tick: 1, weight: 2.0, solidarity: null, tension: 0.2 },
    ];
    const node = adaptEdge(EDGE_REF, { value_flow: 2.0, tension: 0.2 }, history);

    const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
    expect(row?.history).toEqual([1.0, 2.0]);
  });

  it("attaches history to the solidarity_strength row only when that row exists", () => {
    const history: EdgeHistoryPoint[] = [
      { tick: 0, weight: 1.0, solidarity: 0.3, tension: 0.1 },
      { tick: 1, weight: 2.0, solidarity: 0.5, tension: 0.2 },
    ];
    const node = adaptEdge(EDGE_REF, { value_flow: 2.0, solidarity_strength: 0.5 }, history);

    const solidarityRow = node.sections[0]?.rows.find((r) => r.label === "solidarity_strength");
    expect(solidarityRow?.history).toEqual([0.3, 0.5]);
  });

  it("does not fabricate a solidarity history for a non-solidarity edge (no solidarity_strength row at all)", () => {
    const history: EdgeHistoryPoint[] = [{ tick: 0, weight: 1.0, solidarity: null, tension: 0.0 }];
    const node = adaptEdge(EDGE_REF, { value_flow: 1.0, edge_type: "presence" }, history);

    expect(node.sections[0]?.rows.find((r) => r.label === "solidarity_strength")).toBeUndefined();
  });

  it("filters out null/non-finite readings rather than plotting a guessed value", () => {
    const history: EdgeHistoryPoint[] = [
      { tick: 0, weight: 1.0, solidarity: null, tension: 0.0 },
      { tick: 1, weight: null, solidarity: null, tension: 0.0 },
      { tick: 2, weight: 3.0, solidarity: null, tension: 0.0 },
    ];
    const node = adaptEdge(EDGE_REF, { value_flow: 3.0 }, history);

    const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
    expect(row?.history).toEqual([1.0, 3.0]);
  });

  it("leaves every other row untouched", () => {
    const history: EdgeHistoryPoint[] = [{ tick: 0, weight: 1.0, solidarity: null, tension: 0.0 }];
    const node = adaptEdge(
      EDGE_REF,
      { value_flow: 1.0, edge_type: "tribute", source_name: "C001" },
      history,
    );

    const typeRow = node.sections[0]?.rows.find((r) => r.label === "edge_type");
    const sourceRow = node.sections[0]?.rows.find((r) => r.label === "source_name");
    expect(typeRow?.history).toBeUndefined();
    expect(sourceRow?.history).toBeUndefined();
  });

  it("an empty history array leaves the node identical to the no-history call (no dangling empty .history)", () => {
    const withEmpty = adaptEdge(EDGE_REF, { value_flow: 1.0 }, []);
    const withoutArg = adaptEdge(EDGE_REF, { value_flow: 1.0 });
    expect(withEmpty).toEqual(withoutArg);
  });

  it("history defaults to an empty array when the 3rd argument is omitted (backward-compatible with existing callers)", () => {
    const node = adaptEdge(EDGE_REF, { value_flow: 1.0 });
    const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
    expect(row?.history).toBeUndefined();
  });

  it("a history series with every reading null/non-finite attaches no sparkline (all-gap series)", () => {
    const history: EdgeHistoryPoint[] = [{ tick: 0, weight: null, solidarity: null, tension: 0.0 }];
    const node = adaptEdge(EDGE_REF, { value_flow: null }, history);

    const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
    expect(row?.history).toBeUndefined();
  });
});
