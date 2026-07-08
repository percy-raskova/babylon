/**
 * buildPayload contract tests — one case per verb, asserting the EXACT
 * POST body each backend serializer requires (web/game/serializers.py).
 *
 * P0 #4: the old VerbPage spread flat mock params into the body, so all
 * 9 verbs 400'd. These tests pin the serializer contracts client-side:
 * params nesting, per-verb target keys, and enum values (never display
 * labels) in payloads.
 */

import { describe, it, expect } from "vitest";
import { VERB_REGISTRY } from "@/lib/verbs";

describe("buildPayload — serializer contracts", () => {
  it("educate: target under target_community_id, params dict", () => {
    expect(VERB_REGISTRY.educate!.buildPayload("org-1", "comm-1", {})).toEqual({
      org_id: "org-1",
      target_community_id: "comm-1",
      params: {},
    });
  });

  it("aid: nests transfer_amount under params", () => {
    expect(VERB_REGISTRY.aid!.buildPayload("org-1", "c-1", { transfer_amount: 50 })).toEqual({
      org_id: "org-1",
      target_id: "c-1",
      params: { transfer_amount: 50 },
    });
  });

  it("attack: nests mode under params, passes target through", () => {
    expect(VERB_REGISTRY.attack!.buildPayload("org-1", "t-1", { mode: "mass" })).toEqual({
      org_id: "org-1",
      target_id: "t-1",
      params: { mode: "mass" },
    });
  });

  it("attack: defaults mode to 'targeted' and allows a null target", () => {
    expect(VERB_REGISTRY.attack!.buildPayload("org-1", null, {})).toEqual({
      org_id: "org-1",
      target_id: null,
      params: { mode: "targeted" },
    });
  });

  it("mobilize: nests sl_committed number under params", () => {
    expect(VERB_REGISTRY.mobilize!.buildPayload("org-1", "m-1", { sl_committed: 5 })).toEqual({
      org_id: "org-1",
      target_id: "m-1",
      params: { sl_committed: 5 },
    });
  });

  it("campaign: FLAT campaign_type, no params key (BaseVerbActionView contract)", () => {
    const body = VERB_REGISTRY.campaign!.buildPayload("org-1", "terr-1", {
      campaign_type: "ELECTORAL",
    });
    expect(body).toEqual({ org_id: "org-1", target_id: "terr-1", campaign_type: "ELECTORAL" });
    expect(body).not.toHaveProperty("params");
  });

  it("move: nests mode under params, defaults to 'expand'", () => {
    expect(VERB_REGISTRY.move!.buildPayload("org-1", "terr-2", { mode: "relocate" })).toEqual({
      org_id: "org-1",
      target_id: "terr-2",
      params: { mode: "relocate" },
    });
    expect(VERB_REGISTRY.move!.buildPayload("org-1", "terr-2", {})).toEqual({
      org_id: "org-1",
      target_id: "terr-2",
      params: { mode: "expand" },
    });
  });

  it("investigate: nests scan_type under params, target optional", () => {
    expect(
      VERB_REGISTRY.investigate!.buildPayload("org-1", null, { scan_type: "territory_scan" }),
    ).toEqual({
      org_id: "org-1",
      target_id: null,
      params: { scan_type: "territory_scan" },
    });
  });

  it("reproduce: nests mode + labor commitments, omits target_id when null", () => {
    const body = VERB_REGISTRY.reproduce!.buildPayload("org-1", null, {
      mode: "mass_recruitment",
      cl_committed: 2,
      sl_committed: 3,
    });
    expect(body).toEqual({
      org_id: "org-1",
      params: { mode: "mass_recruitment", cl_committed: 2, sl_committed: 3 },
    });
    expect(body).not.toHaveProperty("target_id");
  });

  it("reproduce: includes target_id when a self-target is selected", () => {
    expect(
      VERB_REGISTRY.reproduce!.buildPayload("org-1", "org-1", { mode: "cadre_training" }),
    ).toMatchObject({ org_id: "org-1", target_id: "org-1" });
  });

  it("negotiate: nests proposal under params, defaults to coordination_pact", () => {
    expect(
      VERB_REGISTRY.negotiate!.buildPayload("org-1", "org-9", { proposal: "ceasefire" }),
    ).toEqual({ org_id: "org-1", target_id: "org-9", params: { proposal: "ceasefire" } });
    expect(VERB_REGISTRY.negotiate!.buildPayload("org-1", "org-9", {})).toEqual({
      org_id: "org-1",
      target_id: "org-9",
      params: { proposal: "coordination_pact" },
    });
  });

  it("every verb has a buildPayload", () => {
    for (const config of Object.values(VERB_REGISTRY)) {
      expect(typeof config.buildPayload).toBe("function");
    }
  });
});

describe("select ParamField enum hygiene", () => {
  // Backend serializers validate ChoiceFields against enum literals —
  // display labels ("Study Circle" style) must never appear in values.
  const BACKEND_ENUMS: Record<string, Record<string, string[]>> = {
    attack: { mode: ["targeted", "mass"] },
    campaign: { campaign_type: ["ELECTORAL", "LEGISLATIVE", "PUBLIC_PRESSURE"] },
    move: { mode: ["expand", "relocate"] },
    investigate: { scan_type: ["territory_scan", "targeted_scan", "counter_intelligence"] },
    reproduce: { mode: ["cadre_training", "mass_recruitment"] },
    negotiate: {
      proposal: [
        "coordination_pact",
        "resource_sharing",
        "ceasefire",
        "demand_policy_change",
        "reconciliation",
      ],
    },
  };

  it("every select option value is a backend enum literal (no spaces, no labels)", () => {
    for (const [verb, config] of Object.entries(VERB_REGISTRY)) {
      for (const field of config.paramFields.filter((f) => f.type === "select")) {
        expect(field.options, `${verb}.${field.key} select needs options`).toBeDefined();
        for (const opt of field.options!) {
          expect(opt.value, `${verb}.${field.key} option '${opt.value}'`).toMatch(
            /^[a-z_]+$|^[A-Z_]+$/,
          );
          const enums = BACKEND_ENUMS[verb]?.[field.key];
          if (enums) {
            expect(enums, `${verb}.${field.key}`).toContain(opt.value);
          }
        }
        expect(field.options!.map((o) => o.value)).toContain(field.defaultValue);
      }
    }
  });

  it("select fields cover the full backend enum for each wired verb", () => {
    for (const [verb, fields] of Object.entries(BACKEND_ENUMS)) {
      for (const [key, values] of Object.entries(fields)) {
        const field = VERB_REGISTRY[verb]!.paramFields.find((f) => f.key === key);
        expect(field, `${verb} must expose a '${key}' ParamField`).toBeDefined();
        expect(field!.options!.map((o) => o.value).sort()).toEqual([...values].sort());
      }
    }
  });
});
