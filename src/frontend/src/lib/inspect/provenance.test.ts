/**
 * Pins the frontend mirror against `web/game/provenance.py::METRIC_PROVENANCE`
 * (hand-verified: 9 keys, same `supported_scopes` — see that module's
 * `METRIC_PROVENANCE` dict, spec-113 Lane D).
 */

import { describe, it, expect } from "vitest";
import { isExplainableMetric, explainRefFor, METRIC_PROVENANCE_MIRROR } from "./provenance";

describe("METRIC_PROVENANCE_MIRROR", () => {
  it("has the same 9 keys as the backend manifest", () => {
    expect(Object.keys(METRIC_PROVENANCE_MIRROR).sort()).toEqual(
      [
        "acquiescence_probability",
        "consciousness_drift",
        "exploitation_rate",
        "imperial_rent",
        "labor_aristocracy_ratio",
        "occ",
        "profit_rate",
        "revolution_probability",
        "value_extraction_ratio",
      ].sort(),
    );
  });
});

describe("isExplainableMetric", () => {
  it("global-only metrics are not explainable for hex/org scope", () => {
    expect(isExplainableMetric("exploitation_rate", "global")).toBe(true);
    expect(isExplainableMetric("exploitation_rate", "hex")).toBe(false);
    expect(isExplainableMetric("exploitation_rate", "org")).toBe(false);
  });

  it("profit_rate/occ support both global and hex", () => {
    expect(isExplainableMetric("profit_rate", "global")).toBe(true);
    expect(isExplainableMetric("profit_rate", "hex")).toBe(true);
    expect(isExplainableMetric("profit_rate", "org")).toBe(false);
  });

  it("org-scoped metrics are not explainable elsewhere", () => {
    expect(isExplainableMetric("revolution_probability", "org")).toBe(true);
    expect(isExplainableMetric("revolution_probability", "global")).toBe(false);
  });

  it("an unrecognized metric name is never explainable", () => {
    expect(isExplainableMetric("not_a_real_metric", "global")).toBe(false);
  });
});

describe("explainRefFor", () => {
  it("builds a metric ref with the given scope/label when supported", () => {
    expect(explainRefFor("imperial_rent", "global", "global", "Rent Φ")).toEqual({
      kind: "metric",
      id: "imperial_rent",
      scope: "global",
      label: "Rent Φ",
    });
  });

  it("returns undefined when the scope kind is unsupported", () => {
    expect(explainRefFor("imperial_rent", "org:C001", "org")).toBeUndefined();
  });
});
