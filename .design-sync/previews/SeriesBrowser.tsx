/**
 * SeriesBrowser preview — fetches its own data (`fetchSeries` from
 * `./api`, a direct `fetch()` via the shared API client), NOT the store.
 * The design-sync bundle deliberately never mounts MSW (see
 * design-sync.entry.tsx), so in this static capture environment every
 * `fetch()` resolves against the preview's own static file server, which
 * 404s any `/api/...` path — deterministically, not a timing accident.
 *
 * `scope`/`scopeId`/`metrics`/`series` are internal `useState` with no
 * prop-level override (only `session` and `source` are props, and neither
 * touches scope), so exactly one composition is statically reachable
 * regardless of which session is passed: scope defaults to "national"
 * (always scope-ready) → the effect fires → `fetchSeries` resolves to
 * `null` (404) → `series` never becomes non-null → `matched` never becomes
 * true → the component is stuck on its "Loading…" branch permanently.
 * That's not a spinner mid-flight (which package-capture's `networkidle`
 * wait would in fact settle past) — it is where this component's own
 * logic terminates on a failed fetch (no dedicated error branch). Honest
 * per III.11; the populated chart / scope-FIPS-entry / metric-toggle
 * states all require either a successful fetch or a scope-select
 * interaction, neither reachable here — see learnings.
 */
import { SeriesBrowser } from "babylon-cockpit";

const WAYNE_COUNTY_SESSION = {
  session_id: "fb1850ea-b947-41a4-bc7a-d00389a57b5f",
  min_tick: 0,
  max_tick: 104,
  tick_count: 105,
  checkpoint_count: 2,
  latest_hash: "9f449ac24e67639100b95968f550c6a6089807df798eee48e900073e73990223",
  scenario: "wayne_county_baseline",
  status: "active",
  created_at: "2026-07-09T18:42:07Z",
};

// Inline pixel sizing, not Tailwind arbitrary-value classes — see
// ObservatoryChart.tsx's Frame comment / learnings/observatory.md:
// .design-sync/previews/ isn't in Tailwind's v4 content-detection scan, so
// `w-[900px] h-[500px]` silently compiles to nothing. SeriesBrowser is
// `flex h-full flex-col` internally, so it needs a real ancestor height or
// it collapses.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void" style={{ width: 900, height: 500 }}>
      {children as never}
    </div>
  );
}

export function LoadingNationalScope() {
  return (
    <Frame>
      <SeriesBrowser session={WAYNE_COUNTY_SESSION} source="live" />
    </Frame>
  );
}
