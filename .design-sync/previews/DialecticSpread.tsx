/**
 * DialecticSpread preview — card grid of active contradictions
 * (src/components/takeovers/dialectic/DialecticSpread.tsx). Reads
 * `panels.contradiction` through `useContradiction` — same fetch-on-mount
 * hazard as the chronicle family (see EndStateScreen preview's header),
 * except worse here: DialecticSpread's `{error && <div>Error: …</div>}` is
 * NOT gated on the oppositions list being empty, so an unguarded real
 * fetch would grow a spurious "Error: HTTP 404" banner above real,
 * populated data. `gameId=""` blocks the hook's effect so the seeded
 * panel state is what actually renders.
 *
 * `poleLabels()` only resolves human labels for an opposition whose `key`
 * matches `frame.principal.id` or `frame.secondary.id` — the frame has
 * room for exactly two named aspects. A 3rd+ opposition entry falls back
 * to its raw `key` string and a bare "a"/"b" `leading_pole` letter instead
 * of real labels (read from the component; not exercised below — every
 * populated cell uses exactly 2 oppositions, matching what the frame can
 * actually label).
 */
import { DialecticSpread, useStore } from "babylon-cockpit";

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
      <DialecticSpread gameId="" />
    </Frame>
  );
}

export function SublationRegime() {
  seedContradiction({
    tick: 118,
    regime: "sublation",
    oppositions: [
      { key: "capital_labor", gap: 0.18, rate: -0.06, is_principal: true, leading_pole: "b" },
      { key: "dual_power", gap: 0.09, rate: -0.02, is_principal: false, leading_pole: "a" },
    ],
    principal_key: "capital_labor",
    frame: {
      principal: {
        id: "capital_labor",
        aspect_a: "Labor",
        aspect_b: "Capital",
        principal_aspect: "b",
        intensity: 0.18,
        aspect_balance: -0.06,
        is_antagonistic: false,
      },
      secondary: {
        id: "dual_power",
        aspect_a: "Soviet-Style Councils",
        aspect_b: "Bourgeois State",
        principal_aspect: "a",
        intensity: 0.09,
        aspect_balance: -0.02,
        is_antagonistic: false,
      },
    },
  });
  return (
    <Frame>
      <DialecticSpread gameId="" />
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
      <DialecticSpread gameId="" />
    </Frame>
  );
}
