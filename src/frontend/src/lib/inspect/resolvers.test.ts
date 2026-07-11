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
});
