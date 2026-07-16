/**
 * DoctrineTakeover tests (Epoch 3 Wave 6 Phase 0, the 5th takeover) —
 * fetch-on-open gating, the full 11-node MVP tree rendering, trap/goal node
 * flagging, tag display, the honest read-only/locked framing when there is
 * no player faction (Constitution III.11 — never a fake affordance), and
 * (Unit 7b) the Study affordance: submitting the standing Study order
 * through the existing educate verb and the resulting "Studying" badge.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
      "Click Study on an unlocked node to direct the",
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

  // -------------------------------------------------------------------------
  // Unit 7b — the Study affordance (faction_id / study_target_id).
  // -------------------------------------------------------------------------

  it("renders a Study button on every unacquired, non-trap node when the session has a player faction", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({ faction_id: "faction-red" }),
        }),
      ),
    );
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const electoral = await screen.findByTestId("doctrine-node-electoral_socialism");
    expect(
      within(electoral).getByRole("button", { name: "Study Electoral Socialism" }),
    ).toBeInTheDocument();
    expect(within(electoral).getByTestId("doctrine-study-electoral_socialism")).toBeInTheDocument();
    expect(within(electoral).queryByText("Locked")).not.toBeInTheDocument();
  });

  it("renders zero Study buttons when the session has no player faction", async () => {
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    await screen.findByTestId("doctrine-node-class_consciousness");
    expect(screen.queryAllByTestId(/^doctrine-study-/)).toHaveLength(0);
  });

  it("never renders a Study button on an acquired node or a trap node, even with a player faction", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({
            faction_id: "faction-red",
            acquired_ids: ["class_consciousness"],
          }),
        }),
      ),
    );
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const root = await screen.findByTestId("doctrine-node-class_consciousness");
    expect(
      within(root).queryByTestId("doctrine-study-class_consciousness"),
    ).not.toBeInTheDocument();
    expect(within(root).getByText("Acquired")).toBeInTheDocument();

    const trap = await screen.findByTestId("doctrine-node-liquidationism");
    expect(within(trap).queryByTestId("doctrine-study-liquidationism")).not.toBeInTheDocument();
    expect(within(trap).getByText("Locked")).toBeInTheDocument();
  });

  it("renders a Studying badge and 'Study ordered' footer for the node matching study_target_id", async () => {
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({
            faction_id: "faction-red",
            study_target_id: "democratic_centralism",
          }),
        }),
      ),
    );
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const node = await screen.findByTestId("doctrine-node-democratic_centralism");
    expect(within(node).getByText("Studying")).toBeInTheDocument();
    expect(within(node).getByText("Study ordered")).toBeInTheDocument();
    expect(
      within(node).queryByTestId("doctrine-study-democratic_centralism"),
    ).not.toBeInTheDocument();

    // A sibling unstudied node keeps its ordinary Study button.
    const sibling = await screen.findByTestId("doctrine-node-electoral_socialism");
    expect(within(sibling).getByTestId("doctrine-study-electoral_socialism")).toBeInTheDocument();
  });

  it("clicking Study POSTs the exact educate submit body and, on refetch, flips the node to Studying", async () => {
    let capturedBody: unknown;
    let studyOrdered = false;
    server.use(
      http.get("/api/games/:id/doctrine-tree/", () =>
        HttpResponse.json({
          status: "ok",
          data: makeDoctrineTreePayload({
            faction_id: "faction-red",
            study_target_id: studyOrdered ? "electoral_socialism" : null,
          }),
        }),
      ),
      http.post("/api/games/:id/actions/educate/", async ({ request }) => {
        capturedBody = await request.json();
        studyOrdered = true;
        return HttpResponse.json(
          { status: "ok", data: { action_id: "action-1" } },
          { status: 201 },
        );
      }),
    );
    render(<DoctrineTakeover gameId={DEFAULT_GAME_ID} />);

    const electoral = await screen.findByTestId("doctrine-node-electoral_socialism");
    await userEvent.click(within(electoral).getByTestId("doctrine-study-electoral_socialism"));

    await waitFor(() =>
      expect(capturedBody).toEqual({
        org_id: "faction-red",
        target_community_id: "faction-red",
        params: { doctrine_node_id: "electoral_socialism" },
      }),
    );

    await waitFor(() => {
      const refetched = screen.getByTestId("doctrine-node-electoral_socialism");
      expect(within(refetched).getByText("Studying")).toBeInTheDocument();
      expect(within(refetched).getByText("Study ordered")).toBeInTheDocument();
      expect(
        within(refetched).queryByTestId("doctrine-study-electoral_socialism"),
      ).not.toBeInTheDocument();
    });
  });
});
