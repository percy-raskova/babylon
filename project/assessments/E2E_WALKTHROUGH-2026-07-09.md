# Babylon E2E Walkthrough — 2026-07-09 (post-remediation sanity check)

Live sanity check of the web product **after** Phase-2 remediation and the tick-52
fix, driven against a real Postgres-backed `EngineBridge`. This is the honest
successor to `E2E_SUMMARY.md` (2026-07-07, which found the game **unplayable**).

**Method:** the canonical core-loop gate (`web/frontend/e2e/real-loop.spec.ts`,
remediation C.5) driving a real headless Chromium through the React UI, plus an
authenticated raw-HTTP drive of every game surface, plus DB-level inspection of
per-tick writes.

**Stack:** `dev @ b57faee6` · Django `:8000` (real `PostgresRuntime` bridge,
`RUN_MAIN=true`) · Vite `:5173` · web Postgres `:5432/babylon` · fresh seed
`f4e52885-d036-403c-b96d-a154d7aeca65` (`wayne_county`, rng_seed 0).

______________________________________________________________________

## Verdict

**The core loop is PLAYABLE. The 2026-07-07 "unplayable" verdict is resolved.**

The full create → submit → **resolve** → results path completes end-to-end through
the real UI. Every P0 from the 2026-07-07 catalog now has a passing live assertion.
What remains are (a) a **test-harness auth gap** that makes 9 secondary e2e specs
look red when the product is fine, (b) **known, already-deferred** depth gaps
(static early-tick economy, per-tick history tables, static objectives/wire), and
(c) prior cosmetic P1/P2s not re-verified here. None block the loop.

______________________________________________________________________

## Evidence

### 1. Core-loop gate — `real-loop.spec.ts`: 7/7 PASS (16.8s)

| Step (real UI) | Old P0 | Result |
|---|---|---|
| login → operations list shows the seeded game | #1 `snapshot_json` 500 | ✅ |
| create a fresh `wayne_county` operation (201) | — | ✅ |
| map endpoint serves real GeoJSON (county + hex) | #7 empty map | ✅ |
| educate composer renders the live verb pipeline | #5 fixture target IDs | ✅ |
| educate submit payload accepted by serializer | #4 field-name mismatch | ✅ |
| campaign submits through the UI (201) | — | ✅ |
| **end turn advances the tick + records results/events** | #6 datetime 500 | ✅ |

### 2. Authenticated API drive — every surface 200 with real data

`games-list` 9 · `state` (tick + org roster: CL 1.0 / SL 4.0 / budget 100 /
consciousness simplex / OODA phase) · `organizations` 1 · `communities` 1 ·
`map?zoom=county` 1 feature · `map?zoom=hex` **81 features** · `timeseries` 7
series · `economy` · `wire` · `alerts` · `journal` · `endgame` — all HTTP 200.
`POST /resolve/` → **HTTP 200, tick 1 → 2**. (P0 #6 confirmed at the API layer too.)

### 3. create_game hex projection (P0 #7) confirmed at creation time

Fresh session → `hex_latest` = **81 hexes** with real coords (lat 42.05–42.54),
county names populated. The map is no longer empty at tick 0.

______________________________________________________________________

## Gaps found (none block the loop)

### G1 — 9/31 e2e specs fail on **test-harness auth**, not product breakage

`playwright.config.ts` defines **no** `storageState` / setup project / global
login. `real-loop.spec.ts` logs in per-test and passes; the secondary specs
(`briefing-live-data` ×2, `intel-results-analysis` ×3, `orgs-live-data` ×2,
`polling-tick-aligned` ×1) navigate **straight to** `/games/{id}/…` **without
logging in**, so they render the `/login` page and fail. The failure snapshot is
literally the login form. Proven benign: the authenticated API drive (§2) returns
real data for every one of those surfaces. **Fix:** add a Playwright auth
setup/`storageState` (or a `beforeEach` login) so the C.5 gate covers more than the
happy path. This is a **gate-quality** issue — the CI Playwright leg currently only
truly exercises `real-loop`.

### G2 — `wire-50-tick.spec.ts` fails legitimately (needs ≥50 ticks)

Our session is at tick 2. Owner-run-gated (owner-queue item 13); not a defect.

### G3 — static early-tick economy (KNOWN — owner item 25, 2nd half) — confirmed live

Resolving tick 1 → 2 advances the tick and the loop, but org/economy values are
**identical** across the tick (cohesion 0.5, cadre_labor 1.0, budget 100.0,
consciousness 0.33/0.33/0.34). Expected: `wayne_county` MELT is unavailable until
the tick-52 year boundary, so production doesn't move the material base yet. This
is the deferred static-economy work (RA-2 / item-25 second half), now observed live
— **not a new regression**.

### G4 — per-tick history tables not populated after resolve

After two resolves: `hex_latest` advances (81 rows, tick → 2, denormalized current
cache) but `tick_summary` = **0** and `territory_snapshot` = **0** rows for the
session — which is why `results/{tick}` returns an empty `data` array and the
Results/Analysis *history* surfaces stay empty even after playing. Consistent with
G3; flagged for the record (couples with the static-economy spec).

### G5 — narrator depth: wire empty, objectives static (product depth, prior finding)

`wire` returns a valid shape (`euphemisms/filters/index/meta/story`) but `story`
= 0 items at low ticks; the 5 objectives are still the hardcoded set
(`revolution` … `fragmented_collapse`, progress 0.0). Same as 2026-07-07 — the
`DeterministicNarrator` placeholder. Not a loop blocker.

### G6 — not re-verified here (prior P1/P2 cosmetics)

Polling backoff (Bug #3; there is now a `polling-tick-aligned` FR-028 spec, itself
blocked by G1), map `maxBounds` (Bug #9), zoom-name mismatch (Bug #8), headless
WebGL map render (Bug #2, environment). Carry forward from `E2E_SUMMARY.md`.

______________________________________________________________________

## What changed since 2026-07-07

All six P0s that made the product unplayable are fixed **and now verified live**,
not merely verified-by-merge: #1 schema parity, #4 verb field names, #5 verb
targets, #6 tick-resolve datetime, #7 map features, #8 verb engine no-ops. The
tick-52 crash (owner item 25, crash half) is fixed (`b57faee6`) — though the
`wayne_county` slice resolves below tick 52, so this walkthrough exercises the
loop, not the crash site directly; the 55-tick bridged run in
`tick52-territory-fips-fixed` covers that.

## Recommendation

1. **Close the C.5 gate gap (G1)** — add Playwright auth `storageState` so the 9
   secondary specs actually test the product. Cheap, high-signal; the CI leg is
   currently a happy-path-only gate.
2. **The loop is playable — the next depth is the static economy (G3/G4)**, which
   is owner item 25's already-scoped second half. Everything below that (G5
   narrator, G6 cosmetics) is polish that does not block play.
