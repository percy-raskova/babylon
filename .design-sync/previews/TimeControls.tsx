/**
 * TimeControls preview — the B4 transport (Pause/Step/Play + status
 * indicator). Pure store-driven state machine: each cell seeds
 * `time.status` (+ `playIntent`/`errorMessage`) in its own wrapper.
 * Card shows the primary story only (cfg.overrides.TimeControls.cardMode
 * = "single") — the singleton store makes multi-cell cards lie; per-story
 * captures grade all five machine states truly.
 */
import { TimeControls, useStore } from "babylon-cockpit";

function seedTime(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    time: {
      ...s.time,
      status: "paused",
      playIntent: false,
      errorMessage: null,
      autopauseEventIds: [],
      ...patch,
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  return <div className="flex items-center bg-void p-4">{children as never}</div>;
}

export function Paused() {
  seedTime({ status: "paused" });
  return (
    <Frame>
      <TimeControls gameId="g-preview" />
    </Frame>
  );
}

export function Playing() {
  seedTime({ status: "playing", playIntent: true });
  return (
    <Frame>
      <TimeControls gameId="g-preview" />
    </Frame>
  );
}

export function ResolvingUnderPlay() {
  seedTime({ status: "resolving", playIntent: true });
  return (
    <Frame>
      <TimeControls gameId="g-preview" />
    </Frame>
  );
}

export function Autopaused() {
  seedTime({ status: "autopaused", autopauseEventIds: ["ev-rupture-26163"] });
  return (
    <Frame>
      <TimeControls gameId="g-preview" />
    </Frame>
  );
}

export function LoudFailure() {
  seedTime({ status: "error", errorMessage: "Tick resolution failed: HTTP 502" });
  return (
    <Frame>
      <TimeControls gameId="g-preview" />
    </Frame>
  );
}
