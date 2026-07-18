/**
 * VerbForm — real preview strip driven by `POST /actions/preview/`
 * (Program 17 Wave 1 item W1.2). This replaces the old fixture-driven
 * `predictedEffect`/constant-direction-chip machinery (deleted): the chip
 * shown here reflects the live backend's `estimated_consciousness_delta`/
 * `estimated_heat_delta`, not a hardcoded config sign. Pins the rendering
 * contract: chips + probability + warnings once a real, non-zero preview
 * lands, and NOTHING while pending, absent, or errored (Constitution
 * III.11 — no "unknown" filler, no stale chip, no skeleton).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";
import type { ActionPreviewResult } from "@/types/game";
import type { VerbConfig, VerbTarget } from "@/lib/verbs";
import { parseFlatCost } from "@/lib/verbs/cost";
import { VerbForm } from "./VerbForm";

interface RawTarget {
  community_id: string;
  territory_name: string;
}

const BASE_PREVIEW: ActionPreviewResult = {
  estimated_consciousness_delta: 0,
  estimated_heat_delta: 0,
  action_point_cost: 1,
  success_probability: 0.5,
  affected_territory_ids: [],
  warnings: [],
};

function makeConfig(overrides?: Partial<VerbConfig>): VerbConfig {
  return {
    verb: "educate",
    label: "Educate",
    description: "Fixture verb config.",
    parseTargets: (raw): VerbTarget[] =>
      ((raw.targets ?? []) as RawTarget[]).map((t) => ({
        id: t.community_id,
        label: t.territory_name,
      })),
    paramFields: [],
    buildPayload: (orgId, targetId, params) => ({
      org_id: orgId,
      target_community_id: targetId ?? "",
      params,
    }),
    ...overrides,
  };
}

function stubTargets(): void {
  server.use(
    http.get("/api/games/:id/actions/educate/targets/", () =>
      HttpResponse.json({
        targets: [{ community_id: "comm-1", territory_name: "Downtown" }],
      }),
    ),
  );
}

function stubPreview(overrides?: Partial<ActionPreviewResult>): void {
  server.use(
    http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, () =>
      HttpResponse.json({ status: "ok", data: { ...BASE_PREVIEW, ...overrides } }),
    ),
  );
}

function renderForm(config: VerbConfig): void {
  render(
    <VerbForm
      gameId={DEFAULT_GAME_ID}
      orgId="org-1"
      verb="educate"
      config={config}
      snapshot={makeSnapshot()}
      submitting={false}
      onSubmit={vi.fn()}
    />,
  );
}

async function selectDowntown(): Promise<void> {
  await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());
  await userEvent.click(screen.getByText("Downtown"));
}

describe("VerbForm action preview", () => {
  it("renders nothing before a target is selected (not yet composable)", async () => {
    stubTargets();
    stubPreview({ estimated_consciousness_delta: 0.3 });
    renderForm(makeConfig());

    await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());

    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
    expect(screen.queryByTestId("preview-probability")).not.toBeInTheDocument();
  });

  it("renders nothing while the preview request is pending (no skeleton, no stale chip)", async () => {
    stubTargets();
    let resolvePreview!: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolvePreview = resolve;
    });
    server.use(
      http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, async () => {
        await pending;
        return HttpResponse.json({ status: "ok", data: BASE_PREVIEW });
      }),
    );
    renderForm(makeConfig());

    await selectDowntown();

    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
    expect(screen.queryByTestId("preview-probability")).not.toBeInTheDocument();

    resolvePreview(undefined);
    await waitFor(() => expect(screen.getByTestId("preview-probability")).toBeInTheDocument());
  });

  it("shows delta chips for non-zero estimated deltas once a target is selected", async () => {
    stubTargets();
    stubPreview({ estimated_consciousness_delta: 0.234, estimated_heat_delta: -0.5 });
    renderForm(makeConfig());

    await selectDowntown();

    const chips = await screen.findAllByTestId("predicted-delta");
    expect(chips).toHaveLength(2);
    expect(chips[0]).toHaveTextContent("▲ Consciousness");
    expect(chips[0]!.className).toContain("text-accent-gold");
    expect(chips[1]).toHaveTextContent("▼ Heat");
    expect(chips[1]!.className).toContain("text-accent-crimson");
  });

  it("shows no delta chips but shows the success probability when both deltas are zero", async () => {
    stubTargets();
    stubPreview({ success_probability: 0.684 });
    renderForm(makeConfig());

    await selectDowntown();

    await waitFor(() => expect(screen.getByTestId("preview-probability")).toBeInTheDocument());
    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
    expect(screen.getByTestId("preview-probability")).toHaveTextContent("68% est. success");
  });

  it("renders backend warnings as a muted list", async () => {
    stubTargets();
    stubPreview({ warnings: ["Insufficient cadre labor", "Target already contested"] });
    renderForm(makeConfig());

    await selectDowntown();

    const warnings = await screen.findByTestId("preview-warnings");
    expect(warnings).toHaveTextContent("Insufficient cadre labor");
    expect(warnings).toHaveTextContent("Target already contested");
  });

  it("renders nothing when the preview fetch fails (honest null)", async () => {
    stubTargets();
    let requestSeen = false;
    server.use(
      http.post(`/api/games/${DEFAULT_GAME_ID}/actions/preview/`, () => {
        requestSeen = true;
        return HttpResponse.json({ status: "error", data: null, message: "boom" }, { status: 500 });
      }),
    );
    renderForm(makeConfig());

    await selectDowntown();
    await waitFor(() => expect(requestSeen).toBe(true));
    // Flush the failed fetch's state update before asserting permanent absence.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
    expect(screen.queryByTestId("preview-probability")).not.toBeInTheDocument();
    expect(screen.queryByTestId("preview-warnings")).not.toBeInTheDocument();
  });
});

function stubTargetsWithCost(canAfford = true): void {
  server.use(
    http.get("/api/games/:id/actions/educate/targets/", () =>
      HttpResponse.json({
        targets: [{ community_id: "comm-1", territory_name: "Downtown" }],
        cost: {
          action_points: 1,
          cadre_labor: 3.0,
          sympathizer_labor: 0.0,
          material: 0.0,
          can_afford: canAfford,
          over_budget: false,
          over_budget_penalty: null,
        },
      }),
    ),
  );
}

describe("VerbForm pre-submit cost line (spec-116 FR-116-4.3)", () => {
  it("shows the live resource cost before any target is selected", async () => {
    stubTargetsWithCost();
    stubPreview();
    renderForm(makeConfig({ parseCost: parseFlatCost }));

    await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());

    const costLine = await screen.findByTestId("verb-cost");
    expect(costLine).toHaveTextContent("3 CL");
    // Preview not composable yet (no target): no AP segment, no fabrication.
    expect(costLine).not.toHaveTextContent("AP");
  });

  it("appends the preview's AP cost once a target is selected", async () => {
    stubTargetsWithCost();
    stubPreview();
    renderForm(makeConfig({ parseCost: parseFlatCost }));

    await selectDowntown();

    await waitFor(() => expect(screen.getByTestId("verb-cost")).toHaveTextContent("3 CL · 1 AP"));
  });

  it("flags an unaffordable cost in crimson but never disables submit", async () => {
    stubTargetsWithCost(false);
    stubPreview();
    renderForm(makeConfig({ parseCost: parseFlatCost }));

    await selectDowntown();

    const costLine = screen.getByTestId("verb-cost");
    expect(costLine).toHaveTextContent("insufficient");
    expect(costLine.className).toContain("text-accent-crimson");
    expect(screen.getByRole("button", { name: /submit educate/i })).toBeEnabled();
  });

  it("renders no cost line for a cost-less verb until the preview lands (honest null)", async () => {
    stubTargets(); // no cost envelope, config has no parseCost (campaign-shaped)
    stubPreview();
    renderForm(makeConfig());

    await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());
    expect(screen.queryByTestId("verb-cost")).not.toBeInTheDocument();

    await selectDowntown();
    await waitFor(() => expect(screen.getByTestId("verb-cost")).toHaveTextContent("1 AP"));
  });
});

describe("VerbForm ineligible empty state (spec-116 FR-4.8)", () => {
  it("renders reason + remedy in the empty state when the verb is ineligible (spec-116 FR-4.8)", async () => {
    server.use(
      http.get("/api/games/:id/actions/educate/targets/", () => HttpResponse.json({ targets: [] })),
    );
    render(
      <VerbForm
        gameId={DEFAULT_GAME_ID}
        orgId="org-1"
        verb="educate"
        config={makeConfig()}
        snapshot={makeSnapshot()}
        submitting={false}
        onSubmit={vi.fn()}
        eligibility={{
          verb: "educate",
          eligible: false,
          reason: "No organized community in your territories yet.",
          remedy:
            "No action can organize a community yet — political education unlocks the moment an organized class appears where you operate.",
          can_afford: true,
          afford_note: null,
        }}
      />,
    );
    const empty = await screen.findByTestId("targets-empty");
    expect(empty).toHaveTextContent(
      "No eligible targets yet: No organized community in your territories yet.",
    );
    expect(empty).toHaveTextContent(/political education unlocks/);
  });
});
