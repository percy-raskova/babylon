/**
 * ChronicleTakeover preview — thin overlay wrapper that renders
 * `EndStateScreen` with no `onRestart` (its real, sole composition).
 * Same `gameId=""` + seeded `panels.endgame` pattern as EndStateScreen's
 * own preview — see that file's header for why the fetch-on-mount hazard
 * requires it.
 */
import { ChronicleTakeover, useStore } from "babylon-cockpit";

function seedEndgame(data: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      endgame: { ...s.panels.endgame, loading: false, error: null, data },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return <div className="h-screen w-full bg-void">{children as never}</div>;
}

export function Victory() {
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
      <ChronicleTakeover gameId="" />
    </Frame>
  );
}

export function OperationInProgress() {
  seedEndgame({
    tick: 58,
    outcome: null,
    headline: "",
    summary: "",
    stats: { final_tick: 58, consciousness: 0.39, solidarity_edges: 9, heat: 0.33 },
  });
  return (
    <Frame>
      <ChronicleTakeover gameId="" />
    </Frame>
  );
}
