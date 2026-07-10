/**
 * Verb config registry and parseTargets tests.
 */

import { describe, it, expect } from "vitest";
import { VERB_REGISTRY, VERB_NAMES } from "@/lib/verbs";
import educateTargetsFixture from "@/mocks/educate_targets.json";

describe("VERB_REGISTRY", () => {
  it("contains all 9 verbs", () => {
    expect(VERB_NAMES).toEqual([
      "aid",
      "attack",
      "campaign",
      "educate",
      "investigate",
      "mobilize",
      "move",
      "negotiate",
      "reproduce",
    ]);
  });

  it("every config has required fields", () => {
    for (const [key, config] of Object.entries(VERB_REGISTRY)) {
      expect(config.verb).toBe(key);
      expect(config.label).toBeTruthy();
      expect(config.description).toBeTruthy();
      expect(typeof config.parseTargets).toBe("function");
      expect(Array.isArray(config.paramFields)).toBe(true);
    }
  });
});

describe("educate.parseTargets", () => {
  it("parses the educate targets fixture", () => {
    const config = VERB_REGISTRY.educate!;
    const targets = config.parseTargets(educateTargetsFixture);

    expect(targets).toHaveLength(2);
    expect(targets[0]!.id).toBe("comm-1");
    expect(targets[0]!.label).toContain("Downtown Detroit");
    expect(targets[1]!.id).toBe("comm-2");
    expect(targets[1]!.label).toContain("Dearborn Assembly");
  });

  it("returns empty array for empty targets", () => {
    const config = VERB_REGISTRY.educate!;
    expect(config.parseTargets({})).toEqual([]);
    expect(config.parseTargets({ targets: [] })).toEqual([]);
  });
});

describe("aid.parseTargets", () => {
  it("parses dual target pools", () => {
    const config = VERB_REGISTRY.aid!;
    const targets = config.parseTargets({
      population_targets: [{ community_id: "c-1", community_name: "Corktown" }],
      org_targets: [{ org_id: "o-1", org_name: "Mutual Aid" }],
    });

    expect(targets).toHaveLength(2);
    expect(targets[0]!.group).toBe("Communities");
    expect(targets[1]!.group).toBe("Organizations");
  });
});

describe("attack.parseTargets", () => {
  it("parses nested target groups", () => {
    const config = VERB_REGISTRY.attack!;
    const targets = config.parseTargets({
      targets: {
        organizations: [{ target_id: "t-1", name: "State Police" }],
        institutions: [{ target_id: "t-2", name: "City Council" }],
      },
    });

    expect(targets).toHaveLength(2);
    expect(targets[0]!.group).toBe("Organizations");
    expect(targets[1]!.group).toBe("Institutions");
  });

  it("parses the edges group (AttackTargetEdgeModelSerializer)", () => {
    const config = VERB_REGISTRY.attack!;
    const targets = config.parseTargets({
      targets: {
        organizations: [],
        institutions: [],
        edges: [{ target_id: "e-1", edge_description: "WAGES: plant → landlord" }],
      },
    });

    expect(targets).toHaveLength(1);
    expect(targets[0]!.id).toBe("e-1");
    expect(targets[0]!.label).toBe("WAGES: plant → landlord");
    expect(targets[0]!.group).toBe("Edges");
  });
});

describe("investigate.parseTargets", () => {
  it("parses grouped territory_scans and targeted_scans (InvestigateAvailableTargetsSerializer)", () => {
    const config = VERB_REGISTRY.investigate!;
    const targets = config.parseTargets({
      targets: {
        territory_scans: [{ target_id: "terr-1", name: "Hamtramck" }],
        targeted_scans: [{ target_id: "org-9", name: "DTED" }],
        counter_intelligence: null,
      },
    });

    expect(targets).toHaveLength(2);
    expect(targets[0]!.id).toBe("terr-1");
    expect(targets[0]!.group).toBe("Territory Scans");
    expect(targets[1]!.id).toBe("org-9");
    expect(targets[1]!.group).toBe("Targeted Scans");
  });
});

describe("mobilize.parseTargets", () => {
  it("parses flat target list", () => {
    const config = VERB_REGISTRY.mobilize!;
    const targets = config.parseTargets({
      targets: [
        { id: "m-1", name: "Rally" },
        { id: "m-2", name: "Strike" },
      ],
    });

    expect(targets).toHaveLength(2);
    expect(targets[0]!.id).toBe("m-1");
  });
});

describe("reproduce.parseTargets", () => {
  it("returns empty array when no targets present", () => {
    const config = VERB_REGISTRY.reproduce!;
    expect(config.parseTargets({})).toEqual([]);
  });

  it("parses the self-target list (ReproduceTargetSerializer)", () => {
    const config = VERB_REGISTRY.reproduce!;
    const targets = config.parseTargets({
      targets: [{ target_id: "org-1", name: "WCLF", type: "organization" }],
    });

    expect(targets).toHaveLength(1);
    expect(targets[0]!.id).toBe("org-1");
    expect(targets[0]!.label).toBe("WCLF");
  });
});

describe("Param fields", () => {
  it("aid has transfer_amount number field", () => {
    const fields = VERB_REGISTRY.aid!.paramFields;
    expect(fields).toHaveLength(1);
    expect(fields[0]!.key).toBe("transfer_amount");
    expect(fields[0]!.type).toBe("number");
  });

  it("attack has mode select field", () => {
    const fields = VERB_REGISTRY.attack!.paramFields;
    expect(fields).toHaveLength(1);
    expect(fields[0]!.key).toBe("mode");
    expect(fields[0]!.type).toBe("select");
    expect(fields[0]!.options).toHaveLength(2);
  });

  it("mobilize has sl_committed number field", () => {
    const fields = VERB_REGISTRY.mobilize!.paramFields;
    expect(fields).toHaveLength(1);
    expect(fields[0]!.key).toBe("sl_committed");
  });

  it("educate has no param fields", () => {
    expect(VERB_REGISTRY.educate!.paramFields).toHaveLength(0);
  });
});
