/**
 * evaluatePredictedEffect — pure gating + evaluation logic behind the
 * pre-commit predicted-delta arrows (spec-113 Lane DELTA; vision doc:
 * verbs show "live cost and predicted delta arrows BEFORE you commit").
 *
 * No registry verb carries `predictedEffect` today, so the matrix is
 * driven entirely by fixtures — the honest-null branches (absent
 * selector, no snapshot, no target, zero/non-finite value) are the
 * load-bearing contract (Constitution III.11).
 */

import { describe, it, expect, vi } from "vitest";
import { makeSnapshot } from "@/test/fixtures";
import type { ScriptValue } from "@/lib/selectors/types";
import type { VerbConfig } from "../types";
import { evaluatePredictedEffect } from "../predicted";

function makeEffect(overrides?: Partial<ScriptValue>): ScriptValue {
  return {
    name: "hex.heat.delta",
    label: "Heat",
    description: "Predicted heat delta for the composed action.",
    scopeKind: "hex",
    evaluate: () => 0.25,
    breakdown: () => ({ total: 0.25, contributors: [] }),
    ...overrides,
  };
}

function makeConfig(overrides?: Partial<VerbConfig>): VerbConfig {
  return {
    verb: "educate",
    label: "Educate",
    description: "Fixture verb config.",
    parseTargets: () => [],
    paramFields: [],
    buildPayload: (orgId, targetId, params) => ({
      org_id: orgId,
      target_id: targetId ?? "",
      params,
    }),
    ...overrides,
  };
}

describe("evaluatePredictedEffect", () => {
  it("returns null when the config carries no predictedEffect", () => {
    expect(evaluatePredictedEffect(makeConfig(), makeSnapshot(), "t-1")).toBeNull();
  });

  it("returns null when there is no snapshot", () => {
    const config = makeConfig({ predictedEffect: makeEffect() });
    expect(evaluatePredictedEffect(config, null, "t-1")).toBeNull();
  });

  it("returns null before a target is selected on a target-required verb", () => {
    const config = makeConfig({ predictedEffect: makeEffect() });
    expect(evaluatePredictedEffect(config, makeSnapshot(), null)).toBeNull();
  });

  it("returns null without a target for a non-global scope even when targetRequired is false", () => {
    const config = makeConfig({
      predictedEffect: makeEffect({ scopeKind: "org" }),
      targetRequired: false,
    });
    expect(evaluatePredictedEffect(config, makeSnapshot(), null)).toBeNull();
  });

  it("evaluates with the selected target as the scope focus", () => {
    const evaluate = vi.fn(() => 0.25);
    const config = makeConfig({ predictedEffect: makeEffect({ evaluate }) });
    const snapshot = makeSnapshot();

    evaluatePredictedEffect(config, snapshot, "t-1");

    expect(evaluate).toHaveBeenCalledExactlyOnceWith({
      snapshot,
      this: { kind: "hex", id: "t-1" },
    });
  });

  it("evaluates a global-scope effect with a null focus once the verb is composable", () => {
    const evaluate = vi.fn(() => 0.25);
    const config = makeConfig({
      predictedEffect: makeEffect({ scopeKind: "global", evaluate }),
      targetRequired: false,
    });
    const snapshot = makeSnapshot();

    const delta = evaluatePredictedEffect(config, snapshot, null);

    expect(evaluate).toHaveBeenCalledExactlyOnceWith({ snapshot, this: null });
    expect(delta).toEqual({ direction: "up", label: "Heat", value: 0.25 });
  });

  it("maps a positive delta to direction 'up'", () => {
    const config = makeConfig({ predictedEffect: makeEffect({ evaluate: () => 0.02 }) });
    expect(evaluatePredictedEffect(config, makeSnapshot(), "t-1")).toEqual({
      direction: "up",
      label: "Heat",
      value: 0.02,
    });
  });

  it("maps a negative delta to direction 'down'", () => {
    const config = makeConfig({
      predictedEffect: makeEffect({ label: "Cohesion", scopeKind: "org", evaluate: () => -0.1 }),
    });
    expect(evaluatePredictedEffect(config, makeSnapshot(), "org-2")).toEqual({
      direction: "down",
      label: "Cohesion",
      value: -0.1,
    });
  });

  it("returns null for a zero delta (no arrow at zero — Sparkline precedent)", () => {
    const config = makeConfig({ predictedEffect: makeEffect({ evaluate: () => 0 }) });
    expect(evaluatePredictedEffect(config, makeSnapshot(), "t-1")).toBeNull();
  });

  it("returns null for non-finite deltas (NaN, Infinity)", () => {
    const nanConfig = makeConfig({ predictedEffect: makeEffect({ evaluate: () => Number.NaN }) });
    expect(evaluatePredictedEffect(nanConfig, makeSnapshot(), "t-1")).toBeNull();

    const infConfig = makeConfig({
      predictedEffect: makeEffect({ evaluate: () => Number.POSITIVE_INFINITY }),
    });
    expect(evaluatePredictedEffect(infConfig, makeSnapshot(), "t-1")).toBeNull();
  });
});
