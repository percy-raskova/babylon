import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { InspectionStack } from "./InspectionStack";
import { useStore } from "@/store";
import { resetStore } from "@/test/resetStore";
import { resetMockGameState, DEFAULT_GAME_ID } from "@/test/handlers";

beforeEach(() => {
  resetStore();
  resetMockGameState();
  useStore.getState().session.setActiveGame(DEFAULT_GAME_ID);
});

describe("InspectionStack", () => {
  it("renders nothing when the stack is empty", () => {
    const { container } = render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the current frame's card and a breadcrumb trail for the whole stack", async () => {
    render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    useStore.getState().inspect.push({ kind: "hex", id: "h1", label: "Wayne County" });
    await waitFor(() => expect(screen.getByTestId("inspection-card")).toBeInTheDocument());
    useStore
      .getState()
      .inspect.push({ kind: "metric", id: "profit_rate", scope: "hex:h1", label: "Profit Rate" });
    await waitFor(() => expect(screen.getAllByTestId("inspection-breadcrumb-0")).toHaveLength(1));

    // Root frame is breadcrumb-clickable; the current (last) frame is not.
    expect(screen.getByTestId("inspection-breadcrumb-0")).toHaveTextContent("Wayne County");
    expect(screen.queryByTestId("inspection-breadcrumb-1")).not.toBeInTheDocument();
  });

  it("one-click return to root via the first breadcrumb segment", async () => {
    render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await waitFor(() => expect(useStore.getState().inspect.stack).toHaveLength(1));
    useStore.getState().inspect.push({ kind: "org", id: "o1" });
    await waitFor(() => expect(useStore.getState().inspect.stack).toHaveLength(2));

    fireEvent.click(screen.getByTestId("inspection-breadcrumb-0"));
    expect(useStore.getState().inspect.stack).toHaveLength(1);
  });

  it("Escape pops the top frame, but not when it is pinned", async () => {
    render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await waitFor(() => expect(useStore.getState().inspect.stack).toHaveLength(1));

    fireEvent.keyDown(document, { key: "Escape" });
    expect(useStore.getState().inspect.stack).toHaveLength(0);

    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await waitFor(() => expect(useStore.getState().inspect.stack).toHaveLength(1));
    useStore.getState().inspect.togglePin(0);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(useStore.getState().inspect.stack).toHaveLength(1);
  });

  it("the close-all (×) button clears the whole stack", async () => {
    render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    useStore.getState().inspect.push({ kind: "hex", id: "h1" });
    await waitFor(() => expect(screen.getByTestId("inspection-close-all")).toBeInTheDocument());

    fireEvent.click(screen.getByTestId("inspection-close-all"));
    expect(useStore.getState().inspect.stack).toHaveLength(0);
  });

  it("full recursion through real /explain/ payload shapes: exploitation_rate -> value_extraction_ratio, ending at a depth-limit-free leaf", async () => {
    server.use(
      http.get("/api/games/:id/explain/", ({ request }) => {
        const metric = new URL(request.url).searchParams.get("metric");
        if (metric === "exploitation_rate") {
          return HttpResponse.json({
            status: "ok",
            data: {
              metric: "exploitation_rate",
              scope: "global",
              value: 0.45,
              formula: { name: "exploitation_rate", expression: "e1", doc: "d1" },
              inputs: [
                {
                  name: "exchange_ratio",
                  label: "Exchange ratio",
                  value: 1.82,
                  kind: "metric",
                  ref: "value_extraction_ratio",
                },
              ],
              constants: [],
            },
          });
        }
        return HttpResponse.json({
          status: "ok",
          data: {
            metric: "value_extraction_ratio",
            scope: "global",
            value: 1.82,
            formula: { name: null, expression: "e2", doc: "d2" },
            inputs: [
              {
                name: "value_produced",
                label: "Value produced",
                value: 420,
                kind: "state",
                ref: null,
              },
              {
                name: "rent_extracted",
                label: "Rent extracted",
                value: 344.4,
                kind: "state",
                ref: null,
              },
            ],
            constants: [],
          },
        });
      }),
    );

    render(<InspectionStack gameId={DEFAULT_GAME_ID} />);
    useStore.getState().inspect.push({
      kind: "metric",
      id: "exploitation_rate",
      scope: "global",
      label: "Exploitation Rate",
    });
    await waitFor(() => expect(screen.getByTestId("explain-Exchange ratio")).toBeInTheDocument());
    // At depth 1, the breadcrumb's only (current) entry duplicates the
    // card's own title — both legitimately read "Exploitation Rate", so
    // this asserts the card body specifically rather than a bare
    // `getByText` (which would be ambiguous with two matches).
    expect(
      within(screen.getByTestId("inspection-card")).getByText("Exploitation Rate"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("explain-Exchange ratio"));
    await waitFor(() => expect(useStore.getState().inspect.stack).toHaveLength(2));

    // Same-name discipline: the child card's title equals the exact row label that opened it.
    const card = await screen.findByTestId("inspection-card");
    expect(within(card).getByText("Exchange ratio")).toBeInTheDocument();
    expect(within(card).getByText("Value produced")).toBeInTheDocument();
    expect(within(card).getByText("Rent extracted")).toBeInTheDocument();
    expect(screen.getByTestId("inspection-breadcrumb-0")).toHaveTextContent("Exploitation Rate");
  });
});
