/**
 * VerbPage live-pipeline tests (P0 #4 + 5th P0).
 *
 * Targets must come from gameStore.fetchVerbTargets (the live per-verb
 * GET endpoints, MSW-mocked) or the snapshot (campaign), NEVER from
 * @/fixtures/v2-mock-data. Submissions must carry the exact backend
 * serializer body via VERB_REGISTRY buildPayload.
 *
 * Harness follows tick-resolution-page.test.tsx: seedGameStore pins the
 * /state/ endpoint (SEEDED_SNAPSHOT has player org org-wclf), real
 * timers, MSW capture handlers per test.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { VerbPage } from "@/components/pages/VerbPage";
import { useGameStore } from "@/stores/gameStore";
import { server } from "@/test/server";
import educateTargetsFixture from "@/mocks/educate_targets.json";

function renderVerb(verb: string) {
  return render(
    <MemoryRouter initialEntries={[`/games/g1/actions/${verb}`]}>
      <Routes>
        <Route path="/games/:id/actions/:verb" element={<VerbPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("VerbPage — live verb pipeline", () => {
  it("educate: lists live endpoint targets and submits the serializer contract", async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/games/:id/actions/educate/", async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          status: "ok",
          data: { id: 1, status: "pending", verb: "educate" },
        });
      }),
    );

    renderVerb("educate");

    // Live targets from the MSW educate fixture — the mock COMMUNITIES
    // fixture targets must be gone.
    fireEvent.click(await screen.findByText(/Dearborn Assembly/));
    expect(screen.queryByText("Dearborn Proletarian Workers")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/Queue Educate/));

    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured).toEqual({
      org_id: "org-wclf",
      target_community_id: "comm-2",
      params: {},
    });
  });

  it("aid: nests transfer_amount under params in the POST body", async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.get("/api/games/:id/actions/aid/targets/", () =>
        HttpResponse.json({
          population_targets: [{ community_id: "c-1", community_name: "Corktown" }],
          org_targets: [],
        }),
      ),
      http.post("/api/games/:id/actions/aid/", async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ status: "ok", data: { id: 2, status: "pending", verb: "aid" } });
      }),
    );

    renderVerb("aid");

    // Sole target auto-selects, so its label also shows in the compose
    // panel — click the target-list row (first in DOM order).
    fireEvent.click((await screen.findAllByText("Corktown"))[0]!);
    fireEvent.change(screen.getByRole("slider"), { target: { value: "50" } });
    fireEvent.click(screen.getByText(/Queue Aid/));

    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured).toEqual({
      org_id: "org-wclf",
      target_id: "c-1",
      params: { transfer_amount: 50 },
    });
  });

  it("campaign: snapshot-sourced targets, no targets GET, flat campaign_type body", async () => {
    let targetsGetHit = false;
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.get("/api/games/:id/actions/campaign/targets/", () => {
        targetsGetHit = true;
        return new HttpResponse(null, { status: 405 });
      }),
      http.post("/api/games/:id/actions/campaign/", async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          status: "ok",
          data: { id: 3, status: "pending", verb: "campaign" },
        });
      }),
    );

    renderVerb("campaign");

    // Snapshot territories + hyperedges are the target pool.
    expect((await screen.findAllByText("Hamtramck")).length).toBeGreaterThanOrEqual(1);
    fireEvent.click(screen.getByText("Hamtramck Tenants Union"));
    fireEvent.click(screen.getByText("Electoral"));
    fireEvent.click(screen.getByText(/Queue Campaign/));

    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured).toEqual({
      org_id: "org-wclf",
      target_id: "hx-tenants",
      campaign_type: "ELECTORAL",
    });
    expect(captured).not.toHaveProperty("params");
    expect(targetsGetHit).toBe(false);
  });

  it("select params translate display labels to backend enum values", async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.get("/api/games/:id/actions/attack/targets/", () =>
        HttpResponse.json({
          targets: {
            organizations: [{ target_id: "org-dted", name: "DTED" }],
            institutions: [],
            edges: [],
          },
        }),
      ),
      http.post("/api/games/:id/actions/attack/", async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          status: "ok",
          data: { id: 4, status: "pending", verb: "attack" },
        });
      }),
    );

    renderVerb("attack");

    fireEvent.click((await screen.findAllByText("DTED"))[0]!);
    // Click the display label — the payload must carry the enum value.
    fireEvent.click(screen.getByText("Mass Action"));
    fireEvent.click(screen.getByText(/Queue Attack/));

    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured).toEqual({
      org_id: "org-wclf",
      target_id: "org-dted",
      params: { mode: "mass" },
    });
  });

  it("disabled verbs render the FR-025 rejection copy", () => {
    renderVerb("move");
    expect(screen.getByText(/not yet supported \(spec 061 FR-025\)/)).toBeInTheDocument();
  });

  it("fetches targets once per verb:org key, refetches after invalidation", async () => {
    let getCount = 0;
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () => {
        getCount += 1;
        return HttpResponse.json(educateTargetsFixture);
      }),
    );

    const first = renderVerb("educate");
    await screen.findAllByText(/Downtown Detroit/);
    first.unmount();

    renderVerb("educate");
    await screen.findAllByText(/Downtown Detroit/);
    expect(getCount).toBe(1); // cache hit on the second mount

    // resolveTick() calls invalidateVerbTargets() — the mounted page must
    // refetch on the next render pass.
    useGameStore.getState().invalidateVerbTargets();
    await waitFor(() => expect(getCount).toBe(2));
  });
});
