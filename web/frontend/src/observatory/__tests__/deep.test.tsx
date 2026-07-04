/**
 * MSW contract + component tests for the deep panes (spec-099).
 */

import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { fetchBoundary, fetchConservation, fetchDiff, fetchVerify } from "../deepApi";
import { BoundaryPane, ConservationPane, DeepPanes, VerificationPane } from "../DeepPanes";

const SID = "edf07b2e-ac2f-4ed7-990e-cadd159ed7b2";

describe("deepApi", () => {
  it("fetchVerify unwraps the verdict", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/verify/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "live",
            valid: true,
            min_tick: 0,
            max_tick: 3,
            tick_count: 4,
            checkpoint_ticks: [0],
            expected_checkpoint_cadence: 52,
            verification_scope: "structural",
            anomalies: [],
          },
        }),
      ),
    );
    const r = await fetchVerify(SID, "live");
    expect(r?.valid).toBe(true);
    expect(r?.tick_count).toBe(4);
    expect(r?.verification_scope).toBe("structural");
  });

  it("fetchVerify threads source=archive", async () => {
    let seen = "";
    server.use(
      http.get(`/api/observatory/sessions/${SID}/verify/`, ({ request }) => {
        seen = request.url;
        return HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "archive",
            valid: true,
            min_tick: 0,
            max_tick: 519,
            tick_count: 520,
            checkpoint_ticks: [0, 52],
            expected_checkpoint_cadence: 52,
            verification_scope: "structural",
            anomalies: [],
          },
        });
      }),
    );
    await fetchVerify(SID, "archive");
    expect(seen).toContain("source=archive");
  });

  it("fetchBoundary returns empty-state shape", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/boundary/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "live",
            from_tick: 0,
            to_tick: 3,
            by_flow_type: [],
            rows: [],
            truncated: false,
          },
        }),
      ),
    );
    const r = await fetchBoundary(SID, "live");
    expect(r?.by_flow_type).toEqual([]);
    expect(r?.truncated).toBe(false);
  });

  it("fetchConservation honours the non_ok filter", async () => {
    let seen = "";
    server.use(
      http.get(`/api/observatory/sessions/${SID}/conservation/`, ({ request }) => {
        seen = request.url;
        return HttpResponse.json({ status: "ok", data: { rows: [], truncated: false } });
      }),
    );
    const r = await fetchConservation(SID, "live", true);
    expect(seen).toContain("severity=non_ok");
    expect(r.truncated).toBe(false);
  });

  it("fetchDiff builds the a/b query", async () => {
    let seen = "";
    server.use(
      http.get("/api/observatory/diff/", ({ request }) => {
        seen = request.url;
        return HttpResponse.json({
          status: "ok",
          data: {
            a: SID,
            b: SID,
            source: "live",
            national: [{ tick: 0, a_v_sum: 5, b_v_sum: 5, delta: 0 }],
            commits: {
              a: { min_tick: 0, max_tick: 3, tick_count: 4 },
              b: { min_tick: 0, max_tick: 3, tick_count: 4 },
              tick_count_delta: 0,
              range_delta: 0,
            },
          },
        });
      }),
    );
    const r = await fetchDiff(SID, SID, "live");
    expect(seen).toContain(`a=${SID}`);
    expect(r?.commits.tick_count_delta).toBe(0);
  });
});

function verifyHandler(valid: boolean, anomalies: unknown[] = []) {
  return http.get(`/api/observatory/sessions/${SID}/verify/`, () =>
    HttpResponse.json({
      status: "ok",
      data: {
        session_id: SID,
        source: "live",
        valid,
        min_tick: 0,
        max_tick: 3,
        tick_count: 4,
        checkpoint_ticks: [0],
        expected_checkpoint_cadence: 52,
        verification_scope: "structural",
        anomalies,
      },
    }),
  );
}

describe("deep panes render", () => {
  it("VerificationPane shows a valid verdict with honest structural-only wording", async () => {
    server.use(verifyHandler(true));
    render(<VerificationPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("verify-pane")).toBeInTheDocument());
    // Honest wording (spec-099 fix #1/#2/#7): never claims content/tamper
    // verification — the badge and caption both name the structural-only scope.
    expect(screen.getByText("STRUCTURE OK")).toBeInTheDocument();
    expect(screen.queryByText(/CHAIN VALID/)).not.toBeInTheDocument();
    expect(screen.getByTestId("verify-scope-note")).toHaveTextContent(/hash FORMAT/);
  });

  it("VerificationPane lists anomalies when invalid", async () => {
    server.use(verifyHandler(false, [{ kind: "gap", tick: 2, detail: "committed tick missing" }]));
    render(<VerificationPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("anomalies")).toBeInTheDocument());
    expect(screen.getByText(/gap/)).toBeInTheDocument();
    expect(screen.getByText("STRUCTURE ANOMALY")).toBeInTheDocument();
  });

  it("BoundaryPane shows the empty-state", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/boundary/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "live",
            from_tick: 0,
            to_tick: 3,
            by_flow_type: [],
            rows: [],
            truncated: false,
          },
        }),
      ),
    );
    render(<BoundaryPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("boundary-empty")).toBeInTheDocument());
  });

  it("BoundaryPane shows a truncation indicator when the row cap is hit", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/boundary/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "live",
            from_tick: 0,
            to_tick: 3,
            by_flow_type: [{ flow_type: "drain", row_count: 5500, total_magnitude: 1.0 }],
            rows: [],
            truncated: true,
          },
        }),
      ),
    );
    render(<BoundaryPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("boundary-table")).toBeInTheDocument());
    expect(screen.getByTestId("boundary-truncated")).toHaveTextContent(/truncated/i);
  });

  it("ConservationPane shows the empty-state", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/conservation/`, () =>
        HttpResponse.json({ status: "ok", data: { rows: [], truncated: false } }),
      ),
    );
    render(<ConservationPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("conservation-empty")).toBeInTheDocument());
  });

  it("ConservationPane shows a truncation indicator when the row cap is hit", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/conservation/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            rows: [
              {
                tick: 0,
                scale: "county",
                invariant_name: "value",
                computed_value: 1,
                expected_value: 1,
                residual: 0,
                severity: "ok",
              },
            ],
            truncated: true,
          },
        }),
      ),
    );
    render(<ConservationPane sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("conservation-table")).toBeInTheDocument());
    expect(screen.getByTestId("conservation-truncated")).toHaveTextContent(/truncated/i);
  });

  it("DeepPanes switches tabs", async () => {
    server.use(
      verifyHandler(true),
      http.get(`/api/observatory/sessions/${SID}/boundary/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            source: "live",
            from_tick: 0,
            to_tick: 3,
            by_flow_type: [],
            rows: [],
            truncated: false,
          },
        }),
      ),
    );
    render(<DeepPanes sessionId={SID} source="live" />);
    await waitFor(() => expect(screen.getByTestId("verify-pane")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "boundary" }));
    await waitFor(() => expect(screen.getByTestId("boundary-empty")).toBeInTheDocument());
  });
});
