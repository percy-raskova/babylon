/**
 * SessionPicker preview — pure presentational (sessions + onSelect props;
 * no fetch, no store). Framed at page-detail width: ported from its real
 * usage, full-width inside ObservatoryPage's <main>, not a narrow dock.
 *
 * The populated cell sweeps session variety: an in-progress Wayne County
 * run, a completed run, an archived national 520-tick canonical projection
 * (the 10-checkpoint cadence — 520/52 — mirrors the real canonical-run
 * shape from project memory), and one deliberately sparse/orphan session
 * (null scenario/status/hash/created_at) to exercise every `?? "unknown
 * scenario"` / conditional-suffix fallback the component renders.
 */
import { SessionPicker } from "babylon-cockpit";

const SESSIONS = [
  {
    session_id: "fb1850ea-b947-41a4-bc7a-d00389a57b5f",
    min_tick: 0,
    max_tick: 104,
    tick_count: 105,
    checkpoint_count: 2,
    latest_hash: "9f449ac24e67639100b95968f550c6a6089807df798eee48e900073e73990223",
    scenario: "wayne_county_baseline",
    status: "active",
    created_at: "2026-07-09T18:42:07Z",
  },
  {
    session_id: "b6640e30-9dec-41f5-a514-fa3df8918d42",
    min_tick: 0,
    max_tick: 519,
    tick_count: 520,
    checkpoint_count: 10,
    latest_hash: "767b88362a935bda5b206bf9fadb87c91256ae2bde2471b6238045c241b40016",
    scenario: "wayne_county_uprising",
    status: "completed",
    created_at: "2026-07-06T09:15:33Z",
  },
  {
    session_id: "c06d1cc5-18ff-42b8-9434-6ab183fb4ee1",
    min_tick: 0,
    max_tick: 519,
    tick_count: 520,
    checkpoint_count: 10,
    latest_hash: "797c27c996bdd2ea4b2d9130091730f86b26427d9b4eb553c0f74ab3d55a8ab7",
    scenario: "national_projection",
    status: "archived",
    created_at: "2026-06-28T22:04:51Z",
  },
  {
    session_id: "e6a59789-91ff-479d-a2d4-021261d42ef8",
    min_tick: 0,
    max_tick: 0,
    tick_count: 1,
    checkpoint_count: 0,
    latest_hash: null,
    scenario: null,
    status: null,
    created_at: null,
  },
];

// Inline pixel width, not a Tailwind arbitrary-value class — see
// ObservatoryChart.tsx's Frame comment / learnings/observatory.md:
// .design-sync/previews/ isn't in Tailwind's v4 content-detection scan, so
// `w-[820px]` silently compiles to nothing (confirmed absent from the built
// CSS). A block div would still fill the viewport without it, but that's the
// full 900px capture viewport, not this component's real page-detail width.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void p-2" style={{ width: 820 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  return (
    <Frame>
      <SessionPicker sessions={SESSIONS} onSelect={() => {}} />
    </Frame>
  );
}

export function Empty() {
  return (
    <Frame>
      <SessionPicker sessions={[]} onSelect={() => {}} />
    </Frame>
  );
}
