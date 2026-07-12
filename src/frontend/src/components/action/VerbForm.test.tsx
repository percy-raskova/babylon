/**
 * VerbForm — predicted-delta arrows before commit (spec-113 Lane DELTA).
 *
 * Fixture-driven: no registry verb populates `predictedEffect` today, so
 * these tests inject a `ScriptValue` through a fixture `VerbConfig` and
 * pin the rendering contract: arrow + metric name near the submit button
 * once a verb + target are composed, gold for ▲ / crimson for ▼, and
 * NOTHING rendered when the prediction is absent or empty (Constitution
 * III.11 — no "unknown" filler).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { DEFAULT_GAME_ID } from "@/test/handlers";
import { makeSnapshot } from "@/test/fixtures";
import type { ScriptValue } from "@/lib/selectors/types";
import type { VerbConfig, VerbTarget } from "@/lib/verbs";
import { VerbForm } from "./VerbForm";

interface RawTarget {
  community_id: string;
  territory_name: string;
}

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

describe("VerbForm predicted delta", () => {
  it("renders nothing extra when the config has no predictedEffect (honest null)", async () => {
    stubTargets();
    renderForm(makeConfig());

    await selectDowntown();

    expect(screen.getByRole("button", { name: /submit educate/i })).toBeEnabled();
    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
  });

  it("shows a gold ▲ + metric name only once a target is selected", async () => {
    stubTargets();
    renderForm(makeConfig({ predictedEffect: makeEffect() }));

    await waitFor(() => expect(screen.getByTestId("target-picker")).toBeInTheDocument());
    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Downtown"));

    const delta = screen.getByTestId("predicted-delta");
    expect(delta).toHaveTextContent("▲ Heat");
    expect(delta.className).toContain("text-accent-gold");
    expect(delta.className).not.toContain("text-accent-crimson");
  });

  it("shows a crimson ▼ for a negative predicted delta", async () => {
    stubTargets();
    renderForm(
      makeConfig({
        predictedEffect: makeEffect({ label: "Cohesion", evaluate: () => -0.1 }),
      }),
    );

    await selectDowntown();

    const delta = screen.getByTestId("predicted-delta");
    expect(delta).toHaveTextContent("▼ Cohesion");
    expect(delta.className).toContain("text-accent-crimson");
    expect(delta.className).not.toContain("text-accent-gold");
  });

  it("renders no arrow for a zero predicted delta", async () => {
    stubTargets();
    renderForm(makeConfig({ predictedEffect: makeEffect({ evaluate: () => 0 }) }));

    await selectDowntown();

    expect(screen.queryByTestId("predicted-delta")).not.toBeInTheDocument();
  });
});
