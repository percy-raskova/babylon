/**
 * DoctrineTakeover tests (Epoch 3 Wave 6 Phase 0, the 5th takeover) —
 * fetch-on-open gating, the full 11-node MVP tree rendering, trap/goal node
 * flagging, tag display, and the honest read-only/locked framing
 * (Constitution III.11 — no fake "acquire" affordance since acquisition
 * isn't wired yet).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { DoctrineTakeover } from "./DoctrineTakeover";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { makeDoctrineTreePayload, makeDoctrineNode } from "@/test/fixtures";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

const ALL_NODE_IDS = [
  "class_consciousness",
  "trade_unionism",
  "electoral_socialism",
  "coalition_politics",
  "liquidationism",
  "democratic_centralism",
  "mass_line",
  "united_front",
  "armed_vanguard",
  "urban_guerrilla",
  "adventurism",
];

describe("DoctrineTakeover", () => {
  it("fetches the doctrine-tree panel on mount and marks it mounted", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.doctrineTree.mounted).toBe(true));
    await waitFor(() => expect(useStore.getState().panels.doctrineTree.data).not.toBeNull());
  });

  it("unmounts the panel on unmount (fetch-gating symmetry)", async () => {
    const { unmount } = render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.doctrineTree.mounted).toBe(true));
    unmount();
    expect(useStore.getState().panels.doctrineTree.mounted).toBe(false);
  });

  it("renders all 11 nodes from the mock payload", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByTestId("doctrine-takeover")).toBeInTheDocument());
    for (const id of ALL_NODE_IDS) {
      expect(await screen.findByTestId(`doctrine-node-${id}`)).toBeInTheDocument();
    }
  });

  it("flags trap nodes with a Trap badge and the warning border", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const liquidationism = await screen.findByTestId("doctrine-node-liquidationism");
    expect(within(liquidationism).getByText("Trap")).toBeInTheDocument();
    expect(liquidationism.className).toContain("border-laser");

    const adventurism = await screen.findByTestId("doctrine-node-adventurism");
    expect(within(adventurism).getByText("Trap")).toBeInTheDocument();
    expect(adventurism.className).toContain("border-laser");

    // Non-trap, non-goal nodes carry neither badge.
    const tradeUnionism = await screen.findByTestId("doctrine-node-trade_unionism");
    expect(within(tradeUnionism).queryByText("Trap")).not.toBeInTheDocument();
    expect(within(tradeUnionism).queryByText("Goal")).not.toBeInTheDocument();
  });

  it("flags the goal node (united_front) with a Goal badge and the rupture border", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const unitedFront = await screen.findByTestId("doctrine-node-united_front");
    expect(within(unitedFront).getByText("Goal")).toBeInTheDocument();
    expect(unitedFront.className).toContain("border-rupture");
    expect(within(unitedFront).queryByText("Trap")).not.toBeInTheDocument();
  });

  it("shows the corpus starting tag values", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const tags = await screen.findByTestId("doctrine-tags");
    expect(within(tags).getByTestId("doctrine-tag-class_analysis")).toHaveTextContent("1");
    expect(within(tags).getByTestId("doctrine-tag-mass_link")).toHaveTextContent("1");
    expect(within(tags).getByTestId("doctrine-tag-militancy")).toHaveTextContent("0");
  });

  it("renders every node as honestly locked with its real TL cost, never a fake acquire affordance", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const root = await screen.findByTestId("doctrine-node-class_consciousness");
    expect(within(root).getByText("Locked")).toBeInTheDocument();
    expect(within(root).getByText("FREE")).toBeInTheDocument();

    const electoral = await screen.findByTestId("doctrine-node-electoral_socialism");
    expect(within(electoral).getByText("Locked")).toBeInTheDocument();
    expect(within(electoral).getByText("50 TL")).toBeInTheDocument();

    const trap = await screen.findByTestId("doctrine-node-liquidationism");
    expect(within(trap).getByText("Locked")).toBeInTheDocument();
    expect(within(trap).getByText("Fallen into — not purchased")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: /acquire/i })).not.toBeInTheDocument();
    expect(screen.getByTestId("doctrine-acquisition-note")).toHaveTextContent(
      "Player-directed acquisition (the Study action) is coming",
    );
  });

  it("lights acquired nodes and shows the live theoretical-labour balance", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({
            acquired_ids: ["class_consciousness"],
            theoretical_labor: 42.5,
          }),
        }),
      ),
    );
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const root = await screen.findByTestId("doctrine-node-class_consciousness");
    expect(root).toHaveAttribute("data-acquired", "true");
    expect(within(root).getByText("Acquired")).toBeInTheDocument();
    expect(screen.getByTestId("doctrine-theoretical-labor")).toHaveTextContent("42.5 TL");

    // A node the faction has not reached stays honestly locked.
    const electoral = await screen.findByTestId("doctrine-node-electoral_socialism");
    expect(electoral).toHaveAttribute("data-acquired", "false");
    expect(within(electoral).getByText("Locked")).toBeInTheDocument();
  });

  it("shows a node's warning text when present", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    expect(await screen.findByTestId("doctrine-warning-electoral_socialism")).toHaveTextContent(
      "This path leads toward the Liberal Trap.",
    );
  });

  it("renders an honest empty state when the tree has no nodes", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({ nodes: [], root_id: "" }),
        }),
      ),
    );

    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    await waitFor(() => expect(screen.getByTestId("doctrine-empty")).toBeInTheDocument());
  });

  it("groups a tier's per-trunk nodes under their own trunk column", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({
            nodes: [
              makeDoctrineNode({ id: "class_consciousness", tier: 0, parents: [], trunk: null }),
              makeDoctrineNode({
                id: "electoral_socialism",
                tier: 1,
                parents: ["class_consciousness"],
                trunk: "reformist",
              }),
              makeDoctrineNode({
                id: "democratic_centralism",
                tier: 1,
                parents: ["class_consciousness"],
                trunk: "scientific",
              }),
            ],
          }),
        }),
      ),
    );

    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const tier1 = await screen.findByTestId("doctrine-tier-1");
    expect(within(tier1).getByText("Reformist")).toBeInTheDocument();
    expect(within(tier1).getByText("Scientific")).toBeInTheDocument();
    expect(within(tier1).getByText("Insurrectionist")).toBeInTheDocument();
  });
});
