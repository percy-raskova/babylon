/**
 * Fixtures mirror the REAL `/explain/` response shapes from
 * `web/game/provenance.py`'s manifest (hand-transcribed from that module's
 * `METRIC_PROVENANCE` entries and `tests/unit/web/test_game_explain_view.py`
 * — not invented shapes) per this lane's VERIFY requirement.
 */

import { describe, it, expect } from "vitest";
import { adaptMetric } from "./metric";
import type { ExplainResponse } from "@/types/inspection";

const exploitationRateGlobal: ExplainResponse = {
  metric: "exploitation_rate",
  scope: "global",
  value: 0.45,
  formula: {
    name: "exploitation_rate",
    expression: "Convert exchange ratio to exploitation rate.",
    doc: "Convert exchange ratio to exploitation rate.",
  },
  inputs: [
    {
      name: "exchange_ratio",
      label: "Exchange ratio",
      value: 1.82,
      kind: "metric",
      ref: "value_extraction_ratio",
    },
  ],
  constants: [],
};

const laborAristocracyRatioOrg: ExplainResponse = {
  metric: "labor_aristocracy_ratio",
  scope: "org:C001",
  value: 0.62,
  formula: { name: "labor_aristocracy_ratio", expression: "core_wages / value_produced", doc: "d" },
  inputs: [
    {
      name: "core_wages",
      label: "Core wages (incoming WAGES edge flow)",
      value: 120.0,
      kind: "state",
      ref: null,
    },
    {
      name: "value_produced",
      label: "Value produced (entity wealth)",
      value: 300.0,
      kind: "state",
      ref: null,
    },
  ],
  constants: [],
};

const consciousnessDriftOrg: ExplainResponse = {
  metric: "consciousness_drift",
  scope: "org:C002",
  value: null,
  formula: { name: "consciousness_drift", expression: "dPsi/dt = ...", doc: "d" },
  inputs: [
    {
      name: "core_wages",
      label: "Core wages (incoming WAGES edge flow)",
      value: 80.0,
      kind: "state",
      ref: null,
    },
    {
      name: "value_produced",
      label: "Value produced (entity wealth)",
      value: 200.0,
      kind: "state",
      ref: null,
    },
    {
      name: "current_consciousness",
      label: "Current class consciousness",
      value: 0.4,
      kind: "state",
      ref: null,
    },
    {
      name: "sensitivity_k",
      label: "Sensitivity k (GameDefines)",
      value: null,
      kind: "constant",
      ref: null,
    },
    {
      name: "decay_lambda",
      label: "Decay lambda (GameDefines)",
      value: null,
      kind: "constant",
      ref: null,
    },
    {
      name: "solidarity_pressure",
      label: "Solidarity pressure (formula default)",
      value: 0.0,
      kind: "constant",
      ref: null,
    },
    {
      name: "wage_change",
      label: "Wage change (formula default)",
      value: 0.0,
      kind: "constant",
      ref: null,
    },
  ],
  constants: [
    {
      name: "sensitivity_k",
      label: "Sensitivity k (GameDefines)",
      value: null,
      kind: "constant",
      ref: null,
    },
    {
      name: "decay_lambda",
      label: "Decay lambda (GameDefines)",
      value: null,
      kind: "constant",
      ref: null,
    },
    {
      name: "solidarity_pressure",
      label: "Solidarity pressure (formula default)",
      value: 0.0,
      kind: "constant",
      ref: null,
    },
    {
      name: "wage_change",
      label: "Wage change (formula default)",
      value: 0.0,
      kind: "constant",
      ref: null,
    },
  ],
};

const profitRateGlobal: ExplainResponse = {
  metric: "profit_rate",
  scope: "global",
  value: null,
  formula: {
    name: null,
    expression: "rate of profit = s / (c + v) — not yet computed by any System",
    doc: "No wired engine System computes a per-territory or global c/v/s decomposition yet.",
  },
  inputs: [],
  constants: [],
};

describe("adaptMetric", () => {
  it("recurses: a metric-kind input carries a ref into the next metric (exploitation_rate -> value_extraction_ratio)", () => {
    const node = adaptMetric(
      { kind: "metric", id: "exploitation_rate", scope: "global" },
      exploitationRateGlobal,
    );
    const inputsSection = node.sections.find((s) => s.label === "Inputs");
    const row = inputsSection?.rows.find((r) => r.label === "Exchange ratio");
    expect(row?.value).toBe(1.82);
    expect(row?.ref).toEqual({
      kind: "metric",
      id: "value_extraction_ratio",
      scope: "global",
      label: "Exchange ratio",
    });
  });

  it("WAGES NEVER NAKED: core_wages and value_produced always land in the same Inputs section, adjacent, in backend order", () => {
    const node = adaptMetric(
      { kind: "metric", id: "labor_aristocracy_ratio", scope: "org:C001" },
      laborAristocracyRatioOrg,
    );
    const inputsSection = node.sections.find((s) => s.label === "Inputs");
    const labels = inputsSection?.rows.map((r) => r.label) ?? [];
    const wageIndex = labels.findIndex((l) => /wage/i.test(l));
    const valueIndex = labels.findIndex((l) => /value produced/i.test(l));
    expect(wageIndex).toBeGreaterThanOrEqual(0);
    expect(valueIndex).toBe(wageIndex + 1);
  });

  it("projects the constants section with provenance-note labels, honest null for out-of-reach GameDefines coefficients", () => {
    const node = adaptMetric(
      { kind: "metric", id: "consciousness_drift", scope: "org:C002" },
      consciousnessDriftOrg,
    );
    const constantsSection = node.sections.find((s) => s.label === "Constants");
    expect(constantsSection?.rows).toHaveLength(4);
    const sensitivityK = constantsSection?.rows.find(
      (r) => r.label === "Sensitivity k (GameDefines)",
    );
    expect(sensitivityK?.value).toBeNull();
    const wageChange = constantsSection?.rows.find(
      (r) => r.label === "Wage change (formula default)",
    );
    expect(wageChange?.value).toBe(0.0);
  });

  it("terminal honest-null metric (profit_rate) has no Inputs/Constants sections and shows 'no data' via a null value", () => {
    const node = adaptMetric(
      { kind: "metric", id: "profit_rate", scope: "global" },
      profitRateGlobal,
    );
    expect(node.sections.find((s) => s.label === "Inputs")).toBeUndefined();
    expect(node.sections.find((s) => s.label === "Constants")).toBeUndefined();
    const valueRow = node.sections
      .find((s) => s.label === "Formula")
      ?.rows.find((r) => r.label === "Value");
    expect(valueRow?.value).toBeNull();
  });

  it("same-name discipline: the resolved title equals ref.label (the parent row's exact label) when set", () => {
    const node = adaptMetric(
      { kind: "metric", id: "exploitation_rate", scope: "global", label: "Exploitation Rate" },
      exploitationRateGlobal,
    );
    expect(node.title).toBe("Exploitation Rate");
  });

  it("falls back to the formula name, then the metric key, when ref.label is absent (root frame)", () => {
    const node = adaptMetric(
      { kind: "metric", id: "exploitation_rate", scope: "global" },
      exploitationRateGlobal,
    );
    expect(node.title).toBe("exploitation_rate");
    const terminal = adaptMetric(
      { kind: "metric", id: "profit_rate", scope: "global" },
      profitRateGlobal,
    );
    expect(terminal.title).toBe("profit_rate");
  });
});
