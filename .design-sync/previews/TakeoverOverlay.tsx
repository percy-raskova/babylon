/**
 * TakeoverOverlay preview — the full-screen overlay shell hosting the
 * Chronicle/Dialectic takeovers (Wire is a sibling lane's territory; kept
 * out per "compose a small real child" — WireApp pulls in a much bigger
 * multi-column subtree this lane doesn't own or grade).
 *
 * `position:fixed` content needs a transformed, definitely-sized ancestor
 * to stay confined to the card instead of escaping to the real page
 * viewport. The harness documents `.ds-single` as providing this for
 * `?story=` capture, but Frame below adds its own (`transform` +
 * `h-screen`) so the overlay's size is deterministic rather than resting
 * on that.
 *
 * `gameId=""` on every cell — see EndStateScreen/DialecticSpread previews'
 * headers: it blocks the hosted takeovers' mount-effect fetches so the
 * seeded panel data survives instead of being clobbered by this harness's
 * (backend-less, always-404) real fetch.
 *
 * No "closed" cell: `active: null` renders `null` — literally nothing, on
 * a white card background indistinguishable from a broken capture. That
 * behavior is already pinned by TakeoverOverlay.test.tsx's "renders
 * nothing when no takeover is active" — see learnings.
 */
import { TakeoverOverlay, useStore } from "babylon-cockpit";

function seedTakeover(active: "wire" | "chronicle" | "dialectic") {
  useStore.setState((s: any) => ({
    ui: { ...s.ui, takeover: { active } },
  }));
}

function seedContradiction(data: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      contradiction: { ...s.panels.contradiction, loading: false, error: null, data },
    },
  }));
}

function seedEndgame(data: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      endgame: { ...s.panels.endgame, loading: false, error: null, data },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return (
    <div className="h-screen w-full" style={{ transform: "translateZ(0)" }}>
      {children as never}
    </div>
  );
}

export function DialecticOpen() {
  seedTakeover("dialectic");
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
      <TakeoverOverlay gameId="" />
    </Frame>
  );
}

export function ChronicleOpenPending() {
  seedTakeover("chronicle");
  seedEndgame({
    tick: 58,
    outcome: null,
    headline: "",
    summary: "",
    stats: { final_tick: 58, consciousness: 0.39, solidarity_edges: 9, heat: 0.33 },
  });
  return (
    <Frame>
      <TakeoverOverlay gameId="" />
    </Frame>
  );
}

export function ChronicleOpenVictory() {
  seedTakeover("chronicle");
  seedEndgame({
    tick: 105,
    outcome: "revolutionary_victory",
    headline: "BABYLON FALLS",
    summary:
      "The Wayne County soviet holds every hyperedge east of the river. Imperial Rent Φ reads zero for the third consecutive tick.",
    stats: { final_tick: 105, consciousness: 0.91, solidarity_edges: 41, heat: 0.49 },
  });
  return (
    <Frame>
      <TakeoverOverlay gameId="" />
    </Frame>
  );
}
