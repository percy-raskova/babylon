/**
 * Contract test: trade-flows endpoint (spec 103 US4).
 *
 * Pins the response shape `useTradeFlows` relies on: `{status: "ok", data:
 * TradeFlowsPayload}` per `specs/103-trade-surfaces/contracts/trade-flows.yaml`.
 * Written red-first — MSW has no handler for `/api/games/:id/trade-flows/`
 * until `test/handlers.ts` is updated.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse, TradeFlowsPayload } from "@/types/trade";

const GAME_ID = "wayne-county-001";

describe("trade-flows contract (spec 103 US4)", () => {
  it("GET /api/games/:id/trade-flows/ returns a real TradeFlowsPayload", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/trade-flows/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<TradeFlowsPayload>;

    expect(body.status).toBe("ok");
    expect(typeof body.data.tick).toBe("number");
    expect(typeof body.data.has_data).toBe("boolean");
    expect(Array.isArray(body.data.blocs)).toBe(true);

    if (body.data.blocs.length > 0) {
      const bloc = body.data.blocs[0]!;
      expect(typeof bloc.node_id).toBe("string");
      expect(typeof bloc.label).toBe("string");
      expect(bloc.kind === "international" || bloc.kind === "domestic_rest").toBe(true);
      expect(typeof bloc.latest.phi_year_inflow).toBe("number");
      expect(typeof bloc.latest.bilateral_trade_value).toBe("number");
      expect(typeof bloc.latest.erdi_ratio).toBe("number");
      expect(Array.isArray(bloc.phi_series)).toBe(true);
      expect(Array.isArray(bloc.trade_series)).toBe(true);

      if (bloc.phi_series.length > 0) {
        expect(typeof bloc.phi_series[0]!.tick).toBe("number");
        expect(typeof bloc.phi_series[0]!.magnitude).toBe("number");
      }
    }
  });
});
