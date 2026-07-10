/**
 * DeepPanes preview — the composite's VERIFY/BOUNDARY/CONSERVATION tabs
 * (spec-099). Every tab fetches its own data on mount (`deepApi.ts`, a
 * direct `fetch()`; no store), and the design-sync bundle deliberately
 * never mounts MSW (see design-sync.entry.tsx) — so in this static
 * capture, every `/api/observatory/...` call 404s deterministically
 * against the preview server. Each pane happens to have a real, designed
 * terminal surface for that: `VerificationPane` renders "Verification
 * unavailable" when the fetch comes back null; `BoundaryPane` and
 * `ConservationPane` both fold a failed fetch into their normal
 * honest-empty copy (spec-099's "no rows" states). Those are what's
 * captured below — not spinners, not a bug in the preview.
 *
 * `DeepPanes` itself only exposes VERIFY by default — switching tabs is a
 * click (`setTab` local state, no prop), not statically reachable — so the
 * BOUNDARY/CONSERVATION "tabs" are represented by mounting their
 * `BoundaryPane`/`ConservationPane` exports directly (same session, same
 * honest-empty destination a real tab click would land on). The richest
 * states — a valid/anomaly verify badge, a populated boundary-flow table,
 * a conservation-residual table with ok/warn/alarm severities — all need a
 * real successful fetch and are unreachable here; see learnings.
 */
import { BoundaryPane, ConservationPane, DeepPanes } from "babylon-cockpit";

const SESSION_ID = "fb1850ea-b947-41a4-bc7a-d00389a57b5f";

// Inline pixel sizing, not Tailwind arbitrary-value classes — see
// ObservatoryChart.tsx's Frame comment / learnings/observatory.md:
// .design-sync/previews/ isn't in Tailwind's v4 content-detection scan, so
// `w-[820px]`/`h-[420px]` silently compile to nothing.
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="bg-void p-2" style={{ width: 820 }}>
      {children as never}
    </div>
  );
}

export function VerifyTabUnavailable() {
  return (
    <Frame>
      <div style={{ height: 420 }}>
        <DeepPanes sessionId={SESSION_ID} source="live" />
      </div>
    </Frame>
  );
}

export function BoundaryTabEmpty() {
  return (
    <Frame>
      <BoundaryPane sessionId={SESSION_ID} source="live" />
    </Frame>
  );
}

export function ConservationTabEmpty() {
  return (
    <Frame>
      <ConservationPane sessionId={SESSION_ID} source="live" />
    </Frame>
  );
}
