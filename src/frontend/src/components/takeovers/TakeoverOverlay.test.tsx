/**
 * TakeoverOverlay tests (spec-110 B5) — open/close/escape for each of the
 * four full-screen takeovers, plus content rendering from MSW fixtures
 * mirroring the real `/wire/`, `/contradiction/`, `/endgame/`,
 * `/orgs/network/` endpoint shapes, and panel mount/unmount lifecycle tied
 * to takeover open/close.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TakeoverOverlay } from "./TakeoverOverlay";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
});

describe("TakeoverOverlay", () => {
  it("renders nothing when no takeover is active", () => {
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);
    expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument();
  });

  it("opens the Wire takeover and renders WireApp content from the wire panel fixture", async () => {
    useStore.getState().ui.openTakeover("wire");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("takeover-overlay")).toHaveAttribute("data-takeover", "wire");
    expect(screen.getByText("THE WIRE")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByText("Authorities Report Civil Disturbance in Hamtramck"),
      ).toBeInTheDocument(),
    );
  });

  it("opens the Chronicle takeover and renders EndStateScreen content from the endgame panel fixture", async () => {
    useStore.getState().ui.openTakeover("chronicle");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("takeover-overlay")).toHaveAttribute("data-takeover", "chronicle");
    // The default fixture's outcome is null (operation still in progress) —
    // III.11 honesty: a pending game shows a pending state, not a fabricated one.
    await waitFor(() =>
      expect(
        screen.getByText("Operation in progress — no terminal outcome yet."),
      ).toBeInTheDocument(),
    );
  });

  it("opens the Dialectic takeover and renders DialecticSpread content from the contradiction panel fixture", async () => {
    useStore.getState().ui.openTakeover("dialectic");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("takeover-overlay")).toHaveAttribute("data-takeover", "dialectic");
    await waitFor(() => expect(screen.getByText("Labor")).toBeInTheDocument());
    expect(screen.getByText("Capital")).toBeInTheDocument();
    expect(screen.getByText("crisis")).toBeInTheDocument();
  });

  it("opens the Network takeover and renders NetworkTakeover content from the org-network panel fixture", async () => {
    useStore.getState().ui.openTakeover("network");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("takeover-overlay")).toHaveAttribute("data-takeover", "network");
    // The default fixture is honestly empty (Constitution III.11) — no
    // fabricated nodes.
    await waitFor(() => expect(screen.getByTestId("network-empty")).toBeInTheDocument());
  });

  it("opens the Doctrine takeover and renders DoctrineTakeover content from the doctrine-tree panel fixture", async () => {
    useStore.getState().ui.openTakeover("doctrine");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    expect(screen.getByTestId("takeover-overlay")).toHaveAttribute("data-takeover", "doctrine");
    await waitFor(() =>
      expect(screen.getByTestId("doctrine-node-class_consciousness")).toBeInTheDocument(),
    );
  });

  it("closes via the close button", async () => {
    useStore.getState().ui.openTakeover("dialectic");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByTestId("takeover-close"));
    expect(useStore.getState().ui.takeover.active).toBeNull();
  });

  it("closes via Escape", async () => {
    useStore.getState().ui.openTakeover("wire");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);
    expect(screen.getByTestId("takeover-overlay")).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    expect(useStore.getState().ui.takeover.active).toBeNull();
  });

  it("Wire Index tab renders bloc-flow lines from the trade-flows panel fixture", async () => {
    useStore.getState().ui.openTakeover("wire");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);

    await userEvent.click(screen.getByRole("button", { name: /Wire Index/ }));
    await waitFor(() => expect(screen.getByText("European Union")).toBeInTheDocument());
  });

  it("mounts the wire panel while the Wire takeover is open, unmounts it on close", async () => {
    useStore.getState().ui.openTakeover("wire");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.wire.mounted).toBe(true));

    useStore.getState().ui.closeTakeover();
    await waitFor(() => expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument());
    expect(useStore.getState().panels.wire.mounted).toBe(false);
  });

  it("mounts the network panel while the Network takeover is open, unmounts it on close", async () => {
    useStore.getState().ui.openTakeover("network");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.network.mounted).toBe(true));

    useStore.getState().ui.closeTakeover();
    await waitFor(() => expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument());
    expect(useStore.getState().panels.network.mounted).toBe(false);
  });

  it("mounts the doctrineTree panel while the Doctrine takeover is open, unmounts it on close", async () => {
    useStore.getState().ui.openTakeover("doctrine");
    render(<TakeoverOverlay gameId={DEFAULT_GAME_ID} />);
    await waitFor(() => expect(useStore.getState().panels.doctrineTree.mounted).toBe(true));

    useStore.getState().ui.closeTakeover();
    await waitFor(() => expect(screen.queryByTestId("takeover-overlay")).not.toBeInTheDocument());
    expect(useStore.getState().panels.doctrineTree.mounted).toBe(false);
  });
});
