/**
 * Tests for v2 pages — BriefingPage, OrgsPage, VerbPage, ResultsPage.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { seedGameStore, resetGameStore } from "@/__tests__/helpers/seedSnapshot";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { BriefingPage } from "@/components/pages/BriefingPage";
import { OrgsPage } from "@/components/pages/OrgsPage";
import { VerbPage } from "@/components/pages/VerbPage";
import { ResultsPage } from "@/components/pages/ResultsPage";

function renderAtRoute(path: string, element: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="*" element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// BriefingPage
// ---------------------------------------------------------------------------
beforeEach(() => {
  seedGameStore();
});

afterEach(() => {
  resetGameStore();
});

describe("BriefingPage", () => {
  it("renders the Briefing page heading", () => {
    renderAtRoute("/games/g1", <BriefingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Briefing");
  });

  it("shows current tick number", () => {
    renderAtRoute("/games/g1", <BriefingPage />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders sparkline metrics strip", () => {
    renderAtRoute("/games/g1", <BriefingPage />);
    expect(screen.getByText("HEAT")).toBeInTheDocument();
  });

  it("renders critical event dispatch", () => {
    renderAtRoute("/games/g1", <BriefingPage />);
    expect(screen.getByText(/Informant detected/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// OrgsPage
// ---------------------------------------------------------------------------
describe("OrgsPage", () => {
  it("renders player org in roster", () => {
    renderAtRoute("/games/g1/orgs", <OrgsPage />);
    // Multiple WCLF matches expected; just confirm at least one
    expect(screen.getAllByText("WCLF").length).toBeGreaterThanOrEqual(1);
  });

  it("renders verb grid with Educate", () => {
    renderAtRoute("/games/g1/orgs", <OrgsPage />);
    expect(screen.getAllByText("Educate").length).toBeGreaterThanOrEqual(1);
  });

  it("does not show enemy orgs in player roster", () => {
    renderAtRoute("/games/g1/orgs", <OrgsPage />);
    expect(screen.queryByText("WCSD")).not.toBeInTheDocument();
  });

  it("shows note directing to Intel for enemy orgs", () => {
    renderAtRoute("/games/g1/orgs", <OrgsPage />);
    expect(screen.getByText(/Intel/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// VerbPage
// ---------------------------------------------------------------------------
describe("VerbPage", () => {
  function renderVerb(verb: string) {
    return render(
      <MemoryRouter initialEntries={[`/games/g1/actions/${verb}`]}>
        <Routes>
          <Route path="/games/:id/actions/:verb" element={<VerbPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("renders verb label in heading", () => {
    renderVerb("educate");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Educate/);
  });

  it("shows target-type badge", () => {
    renderVerb("educate");
    // target_type is "community" for educate
    expect(screen.getAllByText(/community/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows eligible community targets for educate", () => {
    renderVerb("educate");
    expect(screen.getAllByText("Dearborn Proletarian Workers").length).toBeGreaterThanOrEqual(1);
  });

  it("shows verb-specific parameter controls", () => {
    renderVerb("educate");
    expect(screen.getAllByText("Method").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Study Circle")).toBeInTheDocument();
  });

  it("shows Queue button", () => {
    renderVerb("educate");
    expect(screen.getByText(/Queue Educate/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ResultsPage
// ---------------------------------------------------------------------------
describe("ResultsPage", () => {
  it("renders the Results heading", () => {
    renderAtRoute("/games/g1/results", <ResultsPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Results");
  });

  it("shows player orgs section", () => {
    renderAtRoute("/games/g1/results", <ResultsPage />);
    expect(screen.getByText(/Player Orgs/)).toBeInTheDocument();
  });
});
