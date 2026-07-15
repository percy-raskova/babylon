import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { resolveRef, refKey } from "./resolvers";

describe("refKey", () => {
  it("combines kind+id+scope, excluding the presentational label", () => {
    expect(refKey({ kind: "hex", id: "87283", scope: "hex:87283" })).toBe("hex:87283:hex:87283");
    expect(refKey({ kind: "hex", id: "87283", scope: "hex:87283", label: "Anything" })).toBe(
      "hex:87283:hex:87283",
    );
  });

  it("treats an absent scope as the empty string, distinct from any real scope value", () => {
    expect(refKey({ kind: "org", id: "o1" })).toBe("org:o1:");
  });
});

describe("resolveRef", () => {
  it("hex/org/node/edge/community all hit GET /api/games/:id/<kind>/<id>/ and adapt the response", async () => {
    server.use(
      http.get("/api/games/:id/hex/:entityId/", () =>
        HttpResponse.json({ status: "ok", data: { county_name: "Wayne County", heat: 0.4 } }),
      ),
    );
    const node = await resolveRef("game-001", { kind: "hex", id: "h1" });
    expect(node.title).toBe("Wayne County");
    expect(node.sections[0]?.rows.find((r) => r.label === "Heat")?.value).toBe(0.4);
  });

  it("resolves an entity ref from ref.inline WITHOUT fetching (pure), preferring inline over the endpoint", async () => {
    // If the fetch path were taken it would return this SENTINEL — asserting the
    // node reflects the inline payload instead proves the endpoint was bypassed.
    server.use(
      http.get("/api/games/:id/hex/:entityId/", () =>
        HttpResponse.json({ status: "ok", data: { county_name: "FROM ENDPOINT", heat: 9.9 } }),
      ),
    );
    const node = await resolveRef("game-001", {
      kind: "hex",
      id: "h1",
      inline: { county_name: "Wayne County", heat: 0.4, population: 8000 },
    });
    expect(node.title).toBe("Wayne County");
    expect(node.sections[0]?.rows.find((r) => r.label === "Heat")?.value).toBe(0.4);
    expect(node.sections[0]?.rows.find((r) => r.label === "Population")?.value).toBe(8000);
    // A field absent from the inline payload stays an honest null (III.11).
    expect(node.sections[0]?.rows.find((r) => r.label === "Dominant Class")?.value).toBeNull();
  });

  it("metric hits GET /explain/?metric=&scope= and adapts the FormulaCard shape", async () => {
    server.use(
      http.get("/api/games/:id/explain/", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("metric")).toBe("imperial_rent");
        expect(url.searchParams.get("scope")).toBe("global");
        return HttpResponse.json({
          status: "ok",
          data: {
            metric: "imperial_rent",
            scope: "global",
            value: 12.5,
            formula: {
              name: null,
              expression: "imperial_rent = state.economy.imperial_rent_pool",
              doc: "d",
            },
            inputs: [],
            constants: [],
          },
        });
      }),
    );
    const node = await resolveRef("game-001", { kind: "metric", id: "imperial_rent" });
    expect(node.sections[0]?.rows.find((r) => r.label === "Value")?.value).toBe(12.5);
  });

  it("defaults a metric ref with no scope to 'global'", async () => {
    let capturedScope = "";
    server.use(
      http.get("/api/games/:id/explain/", ({ request }) => {
        capturedScope = new URL(request.url).searchParams.get("scope") ?? "";
        return HttpResponse.json({
          status: "ok",
          data: {
            metric: "imperial_rent",
            scope: "global",
            value: null,
            formula: { name: null, expression: "e", doc: "d" },
            inputs: [],
            constants: [],
          },
        });
      }),
    );
    await resolveRef("game-001", { kind: "metric", id: "imperial_rent" });
    expect(capturedScope).toBe("global");
  });

  it("throws (loud failure) on a non-ok API response", async () => {
    server.use(
      http.get("/api/games/:id/org/:entityId/", () =>
        HttpResponse.json({ status: "error", message: "Org not found" }, { status: 404 }),
      ),
    );
    await expect(resolveRef("game-001", { kind: "org", id: "ghost" })).rejects.toThrow(
      "Org not found",
    );
  });

  // Audit Wave 4 straggler (task #76): edge kind fetches its history off a
  // SECOND endpoint and splices it onto the value_flow row.
  describe("edge history splicing", () => {
    it("fetches GET /edge/:id/history/ alongside the edge detail and attaches it to value_flow", async () => {
      server.use(
        http.get("/api/games/:id/edge/:entityId/", () =>
          HttpResponse.json({ status: "ok", data: { value_flow: 2.0 } }),
        ),
        http.get("/api/games/:id/edge/:entityId/history/", ({ params }) =>
          HttpResponse.json({
            status: "ok",
            data: {
              edge_id: String(params.entityId),
              history: [
                { tick: 0, weight: 1.0, solidarity: null, tension: 0.0 },
                { tick: 1, weight: 2.0, solidarity: null, tension: 0.0 },
              ],
            },
          }),
        ),
      );

      const node = await resolveRef("game-001", { kind: "edge", id: "C001->C004" });

      const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
      expect(row?.history).toEqual([1.0, 2.0]);
    });

    it("degrades to no sparkline (never a blocking error) when the history fetch itself fails", async () => {
      server.use(
        http.get("/api/games/:id/edge/:entityId/", () =>
          HttpResponse.json({ status: "ok", data: { value_flow: 2.0 } }),
        ),
        http.get("/api/games/:id/edge/:entityId/history/", () =>
          HttpResponse.json({ status: "error", message: "boom" }, { status: 500 }),
        ),
      );

      const node = await resolveRef("game-001", { kind: "edge", id: "C001->C004" });

      const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
      expect(row?.history).toBeUndefined();
      expect(row?.value).toBe(2.0); // the edge detail itself still resolved
    });

    it("an inline edge ref (no fetch at all) carries no history — never a stale/mismatched fetch", async () => {
      server.use(
        http.get("/api/games/:id/edge/:entityId/history/", () =>
          HttpResponse.json({
            status: "ok",
            data: {
              edge_id: "SHOULD-NOT-BE-CALLED",
              history: [{ tick: 0, weight: 9.9, solidarity: null, tension: 0 }],
            },
          }),
        ),
      );

      const node = await resolveRef("game-001", {
        kind: "edge",
        id: "C001->C004",
        inline: { value_flow: 2.0 },
      });

      const row = node.sections[0]?.rows.find((r) => r.label === "value_flow");
      expect(row?.history).toBeUndefined();
    });
  });
});
