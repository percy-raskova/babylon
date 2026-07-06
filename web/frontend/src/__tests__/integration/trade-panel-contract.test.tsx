/**
 * Contract test: trade-panel endpoint (spec 103 US6).
 *
 * Pins the response shape `useTradePanel` relies on: `{status: "ok", data:
 * TradePanelPayload}` per `specs/103-trade-surfaces/contracts/trade-panel.yaml`.
 * Written red-first — MSW has no handler for `/api/games/:id/trade-panel/`
 * until `test/handlers.ts` is updated.
 */

import { describe, it, expect } from "vitest";
import type { ApiResponse, TradePanelPayload } from "@/types/trade";

const GAME_ID = "wayne-county-001";

describe("trade-panel contract (spec 103 US6)", () => {
  it("GET /api/games/:id/trade-panel/ returns a real TradePanelPayload", async () => {
    const res = await fetch(`/api/games/${GAME_ID}/trade-panel/`, {
      credentials: "include",
    });
    const body = (await res.json()) as ApiResponse<TradePanelPayload>;

    expect(body.status).toBe("ok");
    expect(typeof body.data.tick).toBe("number");
    expect(typeof body.data.has_data).toBe("boolean");
    expect(typeof body.data.total_phi_inflow).toBe("number");
    expect(typeof body.data.total_trade).toBe("number");
    expect(Array.isArray(body.data.blocs)).toBe(true);
    expect(Array.isArray(body.data.flow_types)).toBe(true);

    if (body.data.blocs.length > 0) {
      const bloc = body.data.blocs[0]!;
      expect(typeof bloc.node_id).toBe("string");
      expect(typeof bloc.label).toBe("string");
      expect(typeof bloc.phi_inflow).toBe("number");
      expect(typeof bloc.trade).toBe("number");
      expect(typeof bloc.erdi_ratio).toBe("number");
    }

    if (body.data.flow_types.length > 0) {
      const ft = body.data.flow_types[0]!;
      expect(typeof ft.flow_type).toBe("string");
      expect(typeof ft.total).toBe("number");
      expect(typeof ft.tick_count).toBe("number");
    }
  });
});
