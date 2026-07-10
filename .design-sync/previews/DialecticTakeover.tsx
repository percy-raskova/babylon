/**
 * DialecticTakeover preview — thin overlay wrapper that renders
 * `DialecticSpread`. Same `gameId=""` + seeded `panels.contradiction`
 * pattern as DialecticSpread's own preview — see that file's header for
 * why the fetch-on-mount hazard requires it.
 */
import { DialecticTakeover, useStore } from "babylon-cockpit";

function seedContradiction(data: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      contradiction: { ...s.panels.contradiction, loading: false, error: null, data },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return <div className="h-screen w-full bg-void">{children as never}</div>;
}

export function ActiveContradictions() {
  seedContradiction({
    tick: 104,
    regime: "crisis",
    oppositions: [
      { key: "capital_labor", gap: 0.71, rate: 0.03, is_principal: true, leading_pole: "b" },
      { key: "imperial", gap: 0.42, rate: -0.01, is_principal: false, leading_pole: "a" },
    ],
    principal_key: "capital_labor",
    frame: {
      principal: {
        id: "capital_labor",
        aspect_a: "Labor",
        aspect_b: "Capital",
        principal_aspect: "b",
        intensity: 0.71,
        aspect_balance: 0.03,
        is_antagonistic: true,
      },
      secondary: {
        id: "imperial",
        aspect_a: "Core",
        aspect_b: "Periphery",
        principal_aspect: "a",
        intensity: 0.42,
        aspect_balance: -0.01,
        is_antagonistic: true,
      },
    },
  });
  return (
    <Frame>
      <DialecticTakeover gameId="" />
    </Frame>
  );
}

export function NoOppositions() {
  seedContradiction({
    tick: 3,
    regime: "reproduction",
    oppositions: [],
    principal_key: "",
    frame: {
      principal: { id: "", aspect_a: "", aspect_b: "", intensity: 0, aspect_balance: 0 },
      secondary: { id: "", aspect_a: "", aspect_b: "", intensity: 0, aspect_balance: 0 },
    },
  });
  return (
    <Frame>
      <DialecticTakeover gameId="" />
    </Frame>
  );
}
