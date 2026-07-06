/**
 * Contract test: contradiction snapshot endpoint (spec 095).
 *
 * Pins the ContradictionSnapshot response shape that `useContradiction`
 * relies on: `{status: "ok", data: ContradictionSnapshot}` where the
 * snapshot carries tick/regime/oppositions/principal_key/frame per the
 * contract in `specs/095-endgame-chronicle/contracts/contradiction.yaml`.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse } from "@/types/game";
import type { ContradictionSnapshot } from "@/types/dialectic";

const GAME_ID = "wayne-county-001";

describe("contradiction contract (spec 095)", () => {
  it("GET /api/games/:id/contradiction/ returns ContradictionSnapshot", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/contradiction/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ContradictionSnapshot>;

    expect(body.status).toBe("ok");
    const snap = body.data;

    expect(typeof snap.tick).toBe("number");
    expect(["reproduction", "crisis", "sublation"]).toContain(snap.regime);
    expect(Array.isArray(snap.oppositions)).toBe(true);
    expect(typeof snap.principal_key).toBe("string");

    for (const opp of snap.oppositions) {
      expect(typeof opp.key).toBe("string");
      expect(typeof opp.gap).toBe("number");
      expect(typeof opp.rate).toBe("number");
      expect(typeof opp.is_principal).toBe("boolean");
    }

    const frame = snap.frame;
    expect(frame.principal).toBeDefined();
    expect(frame.secondary).toBeDefined();
    expect(typeof frame.principal.aspect_a).toBe("string");
    expect(typeof frame.principal.aspect_b).toBe("string");
    expect(typeof frame.principal.intensity).toBe("number");
  });

  it("exactly one opposition is marked principal", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/contradiction/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<ContradictionSnapshot>;
    const principals = body.data.oppositions.filter((o) => o.is_principal);
    expect(principals.length).toBe(1);
    expect(principals[0]?.key).toBe(body.data.principal_key);
  });
});
