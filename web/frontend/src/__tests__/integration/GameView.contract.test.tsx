/**
 * Integration test: Wayne County Store Contract Validation (v2).
 *
 * Tests the store-level MSW contract: fetch, submit actions, resolve ticks.
 * UI rendering tests were removed when GameShell was replaced by GameRouteShell.
 * Those contracts are now covered by the per-page test suites.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { resetMockState } from "@/test/handlers";
import { useGameStore } from "@/stores/gameStore";

describe("Wayne County Store Contract (v2)", () => {
  beforeEach(() => {
    resetMockState();
    useGameStore.getState().reset();
  });

  describe("Contract 4: Store-level MSW integration", () => {
    it("fetches Wayne County snapshot from MSW and populates store", async () => {
      await useGameStore.getState().fetchState("wayne-county-001");

      const snapshot = useGameStore.getState().snapshot;
      if (!snapshot) throw new Error("snapshot is null");
      expect(snapshot.session_id).toBe("wayne-county-001");
      expect(snapshot.organizations).toHaveLength(1);
      const org = snapshot.organizations[0];
      if (!org) throw new Error("org is null");
      expect(org.name).toBe("Wayne County Organizing Committee");
      expect(org.vanguard).not.toBeNull();
      if (!org.vanguard) throw new Error("vanguard is null");
      expect(org.vanguard.cadre_labor).toBe(1.0);
    });

    it("submitAction with unaffordable verb sets error in store via MSW 400", async () => {
      await useGameStore.getState().fetchState("wayne-county-001");

      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "attack",
        target_id: "C003",
      });

      const error = useGameStore.getState().error;
      expect(error).toContain("Insufficient Cadre Labor");
    });

    it("submitAction with affordable verb deducts resources via MSW", async () => {
      await useGameStore.getState().fetchState("wayne-county-001");

      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });

      const snapshot = useGameStore.getState().snapshot;
      if (!snapshot) throw new Error("snapshot is null");
      const org = snapshot.organizations[0];
      if (!org?.vanguard) throw new Error("org or vanguard is null");
      expect(org.vanguard.budget).toBe(50);
    });

    it("resolveTick advances tick and escalates traps via MSW", async () => {
      await useGameStore.getState().fetchState("wayne-county-001");

      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });
      await useGameStore.getState().submitAction("wayne-county-001", {
        org_id: "ORG001",
        verb: "educate",
        target_id: "C001",
      });

      await useGameStore.getState().resolveTick("wayne-county-001");

      const snapshot = useGameStore.getState().snapshot;
      if (!snapshot) throw new Error("snapshot is null");
      expect(snapshot.tick).toBeGreaterThanOrEqual(1);
      expect(snapshot.traps).toBeDefined();
      if (!snapshot.traps) throw new Error("traps is null");
      expect(snapshot.traps.liberal.score).toBeGreaterThan(0.5);
      expect(snapshot.traps.liberal.severity).toBe("moderate");
      expect(snapshot.traps.active_trap).toBe("liberal");
    });
  });
});
