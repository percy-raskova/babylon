# Program 12 — The Cockpit: top-to-bottom frontend rebuild

**Ratified:** 2026-07-09 (Percy, plan-mode approval after 4 explicit rulings).
**Status:** EXECUTING — Phase A merged except A7 (awaiting owner ruling on design
options); Phase B scaffold (B1) merged early.
**Authority:** this file is the program master; ADR061 records the clean-room decision;
live status lives in the table below + `ai-docs/state.yaml`.

## Why (the three diseases)

Percy found the game layout "completely unintuitive" and Habitability/Heat showed
"no data." Exploration (3 agents + firsthand verification, 2026-07-09) decomposed the UI
problem into three diseases, none of which is React:

1. **A starving API.** The engine computes riches every tick that never crossed the
   bridge: `persist_full_tick`/`persist_tick_summary` had zero production callers (so
   `/timeseries/` was permanently empty), `hex_latest` had ~30 columns with 9 written,
   the summary endpoint returned `{}`, the consciousness simplex was hardcoded
   0.33/0.33/0.34 (a live III.11 violation), and the real LLM narrator was never imported
   by any web module.
2. **An IA at war with the canon.** The ratified design canon
   (`design/mockups/README.md`) prescribes a Paradox-style cockpit; the shipped app was
   ~16 routes with the map as a 60%-width pane, a dead Resolve button, 13 independent 2s
   pollers, and 20% orphaned modules.
3. **One literal bug.** `buildLensLayers` blanked ALL five lenses whenever the
   balkanization block was empty — and it was always empty because spec-070 seeding never
   ran, though the seed data existed and validated.

## Owner rulings (2026-07-09, binding)

1. **UI program now** — engine features (spec-106/107/108) land INTO the new shell.
2. **Cockpit + takeovers** — persistent full-viewport map, docked panels; Wire,
   Chronicle/EndState, Dialectic stay full-screen takeovers; anti-god-page discipline per
   panel (Article V verb taxonomy, dual-graph target separation).
3. **Time: Pause/Step/Play** — client-driven serialized resolve loop, auto-pause on
   critical events; no new backend endpoint initially.
4. **Clean-room React app at `src/frontend/`** — same stack fresh; port high-value
   modules; delete `web/frontend` at cutover; a Claude Design session may iterate visuals.

## Shape

- **Phase A / spec-109 — Data Spine** (backend feeds + static economy + seeds)
- **Phase B / spec-110 — Cockpit Shell** (`src/frontend` scaffold, port, time controls)
- **Phase C / spec-111 — Depth & Narrator** (LLM narrator at the bridge boundary,
  remaining dashboards, design session, Observatory port)
- **Phase D / spec-112 — Cutover & Delete** (re-point configs, delete `web/frontend` with
  a test-port ledger)

Spec numbers 109–112 are reserved for these phases (106–108 remain the engine tail).
Standing rules: TDD, branch from dev, `mise run commit`, `mise run check` green;
engine-touching changes byte-identical `qa:regression` or a documented rebaseline +
proof.md (A7 is the one sanctioned rebaseline).

## Live status (2026-07-09 evening)

| Item | Scope | Status | Commit(s) |
| --- | --- | --- | --- |
| Track 0 | git hygiene: 7 worktrees removed, 72→22 branches, corner committed, dev pushed | ✅ DONE | b8cef899 + push |
| A8 | lens guard decoupled (heat/habitability render without balkanization) | ✅ MERGED | f1a57ff3 |
| A1 | full persistence wired into create/resolve (`tick_summary` + snapshots per tick) | ✅ MERGED | 08e3131a |
| A3+A5 | one map-metric contract (`web/game/map_contract.py`); fake consciousness simplex → honest null | ✅ MERGED | 665e0814 |
| A6 | spec-070 balkanization layer seeds into every web session (owner item 8; faction half of item 12); res-7→res-6 H3 aggregation; `WorldState.factions` round-trip | ✅ MERGED | c5c19e21 |
| A2 | hex projection enriched: habitability end-to-end (graph-threaded, `attributes` JSONB + migration 0013), real org_count/heat_delta/state_fips; III.11-honest Nones documented | ✅ MERGED | b0907b97 |
| A4 | real `/summary/`, `/economy/`, `/communities/` (solidarity-component communities); contract tests | ✅ MERGED | 9addfa94 |
| A7 | static economy — per-tick material-base movement (owner item 25 second half) | ✅ CLOSED (engine layer): Option B merged (two-mode TickDynamics, flow accrual annual÷52, conservation property tests; base_year advances with tick); 520-tick canonical COMPLETED twice, michigan-e2e.json regenerated, A/B determinism 0-row diffs — proof-A7.md Parts 0–6 COMPLETE, `cc4a5303` R-PROOF closed. Web visibility = owner item 30 (lane in flight). | 742e7163 + e75464fe + canonical closure commit |
| B1 | cockpit scaffold at `src/frontend/` (React 19/Vite/Tailwind 4/deck.gl 9.2, port 5174) + tooling guards (ruff/mypy excludes, pre-commit set, mise tasks, CI job) | ✅ MERGED (early — no A dependency) | 30f5512e + 504302bf |
| B2 | port survivors: tokens/types/lib/verbs/selectors + unified `Lens` union + map components as controlled components (172 tests) | ✅ MERGED (stores/shell/routing = B3) | dc384c78 + 115e6fc7 |
| B3+B4 | the cockpit itself: one zustand store (session/world/time/map/panels/ui slices), ONE fetch orchestrator (visibility-gated 2s heartbeat + onTickAdvanced fan-out — the 13 pollers are dead in the new app), Pause/Step/Play state machine (409/5xx/autopause handled, serialized Play proven by MSW request-log tests), login/lobby/game routes, full shell (StatusBar+transport, Outliner, persistent map, ActionComposer with 9 flat verbs + TargetPicker, Inspector, BottomStrip with real timeseries + events). 307 vitest tests. Live-browser drive still pending (B6). | ✅ MERGED | a8c8a9dd + a1187bca |
| P13.1 | determinism-contract reference doc (program 13 item 1 / Amendment Q corollary a) | ✅ MERGED — plus 3 integrity findings (owner item 31: tick_commit hash is an identity stamp, not a content hash) | 66125a22 |
| P13.2 | dense per-tick goldens ×5 scenarios, byte-compared in qa:regression (program 13 COMPLETE; constitution marker → IMPLEMENTED v2.9.1) | ✅ MERGED | 60a919e3 |
| item 30 | web sessions sustain + show the county economy: bridge calculator wiring (was NEVER wired — TickDynamics no-op'd on every web session), wayne county-backed (26163 ×81), flow carry across resolve→persist→hydrate→resolve; acceptance: flow_wage_accrued 0→84M→168M through real resolves. Caveats → items 32 (annual continuity) + Leontief phi pipeline (pre-existing, both runners) | ✅ MERGED | 143a3eed |
| item 27 | old-app Playwright storageState harness — TIER-3 verified live: 8/10 previously-false-red specs now pass authenticated; 2 residual failures are pre-existing spec bugs (item 33) | ✅ MERGED | 1c62fc93 |
| item 31 | envelope.py determinism_hash docstring now describes reality (rename still an owner decision) | ✅ MERGED (docstring half) | d94c82db |
| B5 | takeovers: Wire/Chronicle/Dialectic overlays over the persistent shell + Objectives dock tab (322 tests at lane time) | ✅ MERGED | a7b7a9b2 |
| B6 | **the parity gate, LIVE**: storageState harness + six CI-canon specs driven in a real browser against the real engine. Found THE blocker (CSRF origins missing 5174 — every cockpit POST 403'd) + the 5174 port squatter. After the CSRF fix + two UI fixes: **23/23 PASSED, twice** — Phase-B exit gate GREEN | ✅ MERGED | 0b5fb567 + d5f270b2 + f7fff8ab |
| C2 | edges/state-apparatus/infrastructure dashboards + org/territory history endpoints (get_infrastructure had NEVER existed — api view would AttributeError; honest-empty until the transport substrate writes) | ✅ MERGED | f9ac774c |
| C4 | observatory ported to the cockpit (Cold Collapse palette remap, lazy + gated, own route module) + route registered | ✅ MERGED | 30c5faf1 + d5f270b2 |
| C1 | LLM narrator at the bridge boundary: BABYLON_LLM_NARRATOR flag (default OFF = byte-identical DeterministicNarrator, parity-tested), async fire-and-forget post-tick, III.6 model+prompt pinning, III.11 loud degraded marker, provider mocked in tests | ✅ MERGED | a0054dc5 |
| item 33 | polling spec authenticated (real tick advance proven in DB); orgs spec bug had already dissolved with the item-27 harness (no stale assertion existed — verified live ×4 sessions) | ✅ MERGED | 2491b9ba |

| C3 (substrate) | **Claude Design sync (2026-07-10, Percy-invoked `/design-sync`)**: all 49 cockpit components → claude.ai/design project "Babylon Cockpit" (`9ccdf916-…`), 121 authored preview cells graded good, render check 49/49, conventions header (Cold Collapse contract for the design agent) vocabulary-verified; full-token safelist stylesheet ships (`ds-tailwind-entry.css` — app JIT css only carries used utilities). Durable inputs committed under `.design-sync/` + `src/frontend/design-sync.entry.tsx`. Visual iteration itself remains owner-driven in the Design pane. | ✅ SYNCED | ccf8994c |
| — | **Two production defects found by the preview campaign, fixed TDD**: `wire.css` `.col-wrap` had no flex-basis (triptych collapsed at story=null; IntelColumn mid-word wraps when populated) → `flex: 1 1 0`; `EMPTY_WIRE_FEED` filter colors used unprefixed `var(--rent)`-style tokens that nothing defines → `--babylon-*`. Pinned by `wire.contracts.test.ts`. | ✅ MERGED | 23016c79 |

**PHASE B: COMPLETE (exit gate GREEN — 23/23 live parity, two consecutive runs).**
**PHASE C: substantially complete** (C1 narrator, C2 dashboards, C4 observatory done; **C3 substrate
delivered 2026-07-10** — the component library lives in claude.ai/design; the iteration sessions are
owner-driven; C5 polish deferred until after C3 reshapes visuals).
**PHASE D: gated on Percy** (parity evidence exists; needs green on ≥2 consecutive dev merges +
the owner's explicit go for deleting `web/frontend`).
| — | 3 pre-existing `entities`-key integration failures: verdict = retired pre-Spec-052 contract; tests rewritten to current contract | ✅ MERGED | 0613d508 |
| — | endgame faction xfail: A6 round-trip machinery proven fixed; real blocker re-diagnosed (FASCIST_CONSOLIDATION absolute-count threshold pre-empts REVOLUTIONARY_VICTORY — owner-queue item 28) | ✅ MERGED (accurate xfail) | e0338924 |

Wave-1 execution: 6 parallel Sonnet worktree lanes orchestrated by Fable (ultracode),
~50 min wall, 1.23M subagent tokens, 0 errors, all branches rebased + ff-merged linearly.

**Phase A exit gate** (remaining): A7 lands after the owner ruling → live acceptance
(seed wayne_county, resolve 5 ticks, assert non-empty `/summary/`, `/timeseries/`,
`/economy/`, `/communities/`, balkanization block, populated `hex_latest`) → then Phase B
parity measurement sees the real data shape.

## Store/data-layer architecture (Phase B target)

Single Zustand store, sliced; ONE fetch orchestrator replaces the old app's 13
independent 2s pollers: one heartbeat `GET /state/` (2s, tab-visible); fan-out fetches
fire on tick change / panel mount / selection change; a local resolve completion calls
the same `onTickAdvanced(tick)` path. Slices: session, time (resolve state machine:
`paused|playing|resolving|autopaused|error`), world, map (one lens discriminated union —
the spec-093 set primary, metric ramps as a `metric` lens with sub-select), panels/*
(each owning its endpoint + MSW contract test), ui.

## Key risks

- **Resolve latency under Play** — loop serialized by construction; measure; adaptive gap.
- **Seeding/baselines** — A6 seeds at the bridge layer only (headless baselines
  untouched, proven 5/5 byte-identical); A7 is the one sanctioned rebaseline.
- **Scope creep** — the canon cockpit defines REQUIRED panels; Phase B exit is loop
  parity, not route parity.
- **God-page regression** — anti-god-page rules enforced structurally + IX.1 compliance
  pass at B and C exits.

## Deferred (unchanged roadmap, after this program)

Phase-5 engine wiring (gamma-ATUS, Vol-II/III, tensor hierarchy), spec-106 national perf
→ 105 capstone, spec-107 Spectrum σ, spec-108 Transport (both land into the new shell),
fork-ledger Part-2b (awaits Percy's 15 rulings), SSE/websocket, batch/async resolve.
