/**
 * EndStateScreen preview — the Chronicle end-screen for terminal outcomes
 * (src/components/takeovers/chronicle/EndStateScreen.tsx). Reads
 * `panels.endgame` through the `useEndgame` hook, which fetches on mount
 * whenever `gameId` is truthy. This harness has no backend, so that fetch
 * always resolves fast to an error ("HTTP 404") — which never clobbers
 * `data` (panelFactory only touches `loading`/`error` on failure) but DOES
 * clobber `error`, and the pending branch picks its text from `error`
 * before falling back to the honest "Operation in progress" copy. An
 * unguarded real fetch would silently replace our intended empty state
 * with "Error: HTTP 404". Passing `gameId=""` short-circuits the hook's
 * effect (`if (!gameId) return`), so the seeded panel state is what
 * actually renders.
 *
 * `onRestart` is a real prop but has zero call sites — `ChronicleTakeover`
 * (the only current caller) never passes it — omitted here to match
 * production composition exactly.
 */
import { EndStateScreen, useStore } from "babylon-cockpit";

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

export function RevolutionaryVictory() {
  seedEndgame({
    tick: 104,
    outcome: "revolutionary_victory",
    headline: "BABYLON FALLS",
    summary:
      "Wayne County's dual-power network crossed the solidarity threshold: UAW Local 600, the Hamtramck tenant councils, and the eastside block clubs fused into one organ of proletarian rule. P(S|R) exceeded P(S|A) for the industrial proletariat; Imperial Rent Φ collapsed as the reserve army absorbed into cadre.",
    stats: { final_tick: 104, consciousness: 0.87, solidarity_edges: 34, heat: 0.58 },
  });
  return (
    <Frame>
      <EndStateScreen gameId="" />
    </Frame>
  );
}

export function FascistConsolidationDefeat() {
  seedEndgame({
    tick: 118,
    outcome: "fascist_consolidation",
    headline: "THE BUNKER FAILS",
    summary:
      "Reserve-army agitation routed to the revanchist bloc before solidarity density crossed threshold. Institutionalist-Bonapartist factions consolidated emergency powers across Wayne County's institutions; the organizing committee went to ground.",
    stats: { final_tick: 118, consciousness: 0.21, solidarity_edges: 4, heat: 0.91 },
  });
  return (
    <Frame>
      <EndStateScreen gameId="" />
    </Frame>
  );
}

export function OperationInProgress() {
  seedEndgame({
    tick: 62,
    outcome: null,
    headline: "",
    summary: "",
    stats: { final_tick: 62, consciousness: 0.42, solidarity_edges: 11, heat: 0.35 },
  });
  return (
    <Frame>
      <EndStateScreen gameId="" />
    </Frame>
  );
}
