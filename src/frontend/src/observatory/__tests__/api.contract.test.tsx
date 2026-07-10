/**
 * MSW contract tests for the Observatory API client (spec-096).
 *
 * Pins each `/api/observatory/*` endpoint's response envelope and the client's
 * parsing (unwrap `{status,data}`, graceful null/[] on error / disabled 404).
 */

import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import {
  fetchCommits,
  fetchSeries,
  fetchSessions,
  fetchStatus,
  fetchTickRange,
  seriesCsvUrl,
} from "../api";
import { seriesToCsv } from "../csv";
import type { ValueAggregatePoint } from "../types";

const SID = "bc680a68-0000-4000-8000-000000000000";

describe("observatory api client", () => {
  it("fetchStatus returns the flag payload when enabled", async () => {
    server.use(
      http.get("/api/observatory/status/", () =>
        HttpResponse.json({ status: "ok", data: { enabled: true, sim_alias: "sim" } }),
      ),
    );
    const status = await fetchStatus();
    expect(status).toEqual({ enabled: true, sim_alias: "sim" });
  });

  it("fetchStatus returns null when the feature is disabled (404)", async () => {
    server.use(
      http.get("/api/observatory/status/", () => new HttpResponse("Not Found", { status: 404 })),
    );
    expect(await fetchStatus()).toBeNull();
  });

  it("fetchSessions unwraps the session list", async () => {
    server.use(
      http.get("/api/observatory/sessions/", () =>
        HttpResponse.json({
          status: "ok",
          data: [
            {
              session_id: SID,
              min_tick: 0,
              max_tick: 3,
              tick_count: 4,
              checkpoint_count: 1,
              latest_hash: "a".repeat(64),
              scenario: "wayne_county",
              status: "active",
              created_at: null,
            },
          ],
        }),
      ),
    );
    const sessions = await fetchSessions();
    expect(sessions).toHaveLength(1);
    expect(sessions[0]?.session_id).toBe(SID);
    expect(sessions[0]?.tick_count).toBe(4);
  });

  it("fetchSessions returns [] on error", async () => {
    server.use(
      http.get("/api/observatory/sessions/", () => new HttpResponse(null, { status: 503 })),
    );
    expect(await fetchSessions()).toEqual([]);
  });

  it("fetchTickRange unwraps the range", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/ticks/`, () =>
        HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            min_tick: 0,
            max_tick: 3,
            tick_count: 4,
            checkpoint_ticks: [0],
          },
        }),
      ),
    );
    const range = await fetchTickRange(SID);
    expect(range?.checkpoint_ticks).toEqual([0]);
  });

  it("fetchSeries requests the correct scope and unwraps points", async () => {
    let seenUrl = "";
    server.use(
      http.get(`/api/observatory/sessions/${SID}/series/`, ({ request }) => {
        seenUrl = request.url;
        return HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            scope: "county",
            scope_id: "26163",
            from_tick: 0,
            to_tick: 3,
            points: [
              {
                tick: 0,
                c_sum: 10,
                v_sum: 5,
                s_sum: 3,
                k_sum: 100,
                biocapacity_sum: 20,
                hex_count: 2,
              },
            ],
          },
        });
      }),
    );
    const series = await fetchSeries(SID, "county", "26163");
    expect(seenUrl).toContain("scope=county");
    expect(seenUrl).toContain("scope_id=26163");
    expect(series?.points).toHaveLength(1);
  });

  it("fetchSeries omits scope_id for national", async () => {
    let seenUrl = "";
    server.use(
      http.get(`/api/observatory/sessions/${SID}/series/`, ({ request }) => {
        seenUrl = request.url;
        return HttpResponse.json({
          status: "ok",
          data: {
            session_id: SID,
            scope: "national",
            scope_id: "USA",
            from_tick: 0,
            to_tick: 0,
            points: [],
          },
        });
      }),
    );
    await fetchSeries(SID, "national", "");
    expect(seenUrl).toContain("scope=national");
    expect(seenUrl).not.toContain("scope_id");
  });

  it("fetchCommits unwraps the chain", async () => {
    server.use(
      http.get(`/api/observatory/sessions/${SID}/commits/`, () =>
        HttpResponse.json({
          status: "ok",
          data: [
            {
              tick: 0,
              determinism_hash: "0".repeat(64),
              hex_rows_written: 2,
              is_checkpoint: true,
              created_at_utc: null,
            },
          ],
        }),
      ),
    );
    const commits = await fetchCommits(SID);
    expect(commits[0]?.is_checkpoint).toBe(true);
    expect(commits[0]?.determinism_hash).toHaveLength(64);
  });

  it("seriesCsvUrl builds the download URL", () => {
    expect(seriesCsvUrl(SID, "county", "26163")).toBe(
      `/api/observatory/sessions/${SID}/series.csv/?scope=county&scope_id=26163`,
    );
    expect(seriesCsvUrl(SID, "national", "")).toBe(
      `/api/observatory/sessions/${SID}/series.csv/?scope=national`,
    );
  });
});

describe("seriesToCsv", () => {
  it("emits a header row plus one row per point", () => {
    const points: ValueAggregatePoint[] = [
      { tick: 0, c_sum: 10, v_sum: 5, s_sum: 3, k_sum: 100, biocapacity_sum: 20, hex_count: 2 },
      { tick: 1, c_sum: 11, v_sum: 6, s_sum: 4, k_sum: 110, biocapacity_sum: 21, hex_count: 2 },
    ];
    const csv = seriesToCsv(points);
    const lines = csv.split("\n");
    expect(lines[0]).toBe("tick,c_sum,v_sum,s_sum,k_sum,biocapacity_sum,hex_count");
    expect(lines).toHaveLength(3); // header + 2 rows
    expect(lines[1]).toBe("0,10,5,3,100,20,2");
  });
});
