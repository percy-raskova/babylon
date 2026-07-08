# Owner-Review Queue — Program 09

**Status**: All 11 original items RULED by Percy (2026-07-04 handoff).
**New items**: 10 additional items from Waves 16-18 (remediation + new specs).
**Total**: 21 items.

## Original 11 Items (all RULED)

| #   | Item                                                                                            | Percy's Ruling                                                                                                        | Status                                                               |
| --- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1   | Article VII Cold Collapse amendment (from 090, R-VII)                                           | "Percy approves this."                                                                                                | ✅ Ratified                                                          |
| 2   | E:071 fascist_alignment ratchet — monotonic by design; should sub-threshold alignment decay?    | "For now, just monotonic and we can expand as necessary. Nail the basic mechanics first before getting more complex." | ✅ Ruled: monotonic for now                                          |
| 3   | E:101 `_NODE_TO_BLOC` Φ-attribution crosswalk (india/latin_america→Φ=0; russia_csi→Europe weak) | "I ratify this."                                                                                                      | ✅ Ratified                                                          |
| 4   | E:101/104/105 scope-renorm drain magnitude — national scope required?                           | "Yes, national scope is required and ideally international scope as well bc colonisation!"                            | ✅ Ruled: national required, international desired                   |
| 5   | SYSTEMIC: III.7 determinism-hash gate non-functional for cross-run                              | "Approve."                                                                                                            | ✅ Approved (value-comparison is workaround; schema change approved) |
| 6   | O:099 hash pane relabeled "STRUCTURE OK"; hex/ archive endpoint 501; want schema changes?       | "Yes, I approve the schema change."                                                                                   | ✅ Approved                                                          |
| 7   | D:098 Oakland conflict — LODES says net IMPORTER, 3 tests assume exporter                       | "Investigate data to confirm, then correct based on findings."                                                        | ✅ Ruled: investigate then correct                                   |
| 8   | W:093 balkanization seed gap — no scenario seeds spec-070 data                                  | "Yes, this is in scope!"                                                                                              | ✅ Ruled: IN SCOPE                                                   |
| 9   | E:102 gamma shipped-but-inert — wire now or later?                                              | "Wire now or at some point during your work whenever it makes sense."                                                 | ✅ Ruled: wire now                                                   |
| 10  | spec-100/101 trade column naming — USD vs tons                                                  | "Confirmed."                                                                                                          | ✅ Confirmed: USD                                                    |
| 11  | W:092 eventClassifier UPPERCASE-key casing + journal-event id UUID5                             | "Fix it however you see best fit. No need to worry about backward compatibility - just fix it!"                       | ✅ Ruled: fix it, no backward compat                                 |

## New Items from Waves 16-18

| #   | Item                                                                                           | Status                                                                             | Action Needed                                                               |
| --- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 12  | W:093 cross-lane: `WorldState.from_graph()` crashes on faction/sovereign/community nodes       | LATENT (not blocking — no production code path adds these nodes to the main graph) | E-lane follow-up task when spec-070 graph integration lands                 |
| 13  | W:094 Playwright e2e — needs live 50+ tick seeded session                                      | Owner-run, gated on SPEC061_TEST_SESSION_ID                                        | Percy to run                                                                |
| 14  | W:094 Manufacturing Consent filter detection — static rules, real detection needs LLM          | Documented as Known Gap                                                            | M8/Wave-6 spec                                                              |
| 15  | W:094 Hegemony-driven visibility — no-op pass-through                                          | Documented as deferred                                                             | Spec-077 supplies mechanic                                                  |
| 16  | E:104 ContradictionFieldSystem hotspot — 182.6ms/tick, scales super-linearly at national scope | **BLOCKER for E:105 national run**                                                 | Algorithmic investigation (potential R-PROOF); needs optimization spec      |
| 17  | E:104 National hex hydration optimization — >10min for 3,156 counties                          | **BLOCKER for E:105 national run**                                                 | Batch QCEW/BEA lookups, parallelize county processing                       |
| 18  | E:104 Budget measurement variance — 2× between runs                                            | The 2× headroom may not catch real regressions                                     | Consider tighter budget after variance study                                |
| 19  | E:105 National run did NOT complete — tick loop too slow (>30min/tick at national scale)       | **BLOCKED on items 16+17**                                                         | ContradictionFieldSystem optimization + hydration optimization needed first |
| 20  | W:095 EndgameDetector stale docstring — says REVOLUTIONARY_VICTORY-first, code checks it last  | Cross-lane (engine code, `src/babylon/engine/observers/endgame_detector.py`)       | E-lane follow-up: update docstring to match FR-033 order                    |
| 21  | E:104 `qa:tick-budget` — Percy needs to ratify the budget number                               | The budget was set at 2× measured Michigan-statewide values                        | Percy to ratify (per master plan §6 item 4)                                 |

## New Decisions Needed from Percy

| #   | Decision                                                                                                             | Context                                                                                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | #18 risk posture — hex_spatial_map is still globally wipeable; session-scoping is a schema change                    | The #18 fix isolated one test fixture but didn't session-scope the table. Is session-scoping approved, or is the STEP-0 guard sufficient?                                                 |
| B   | Tick-budget number ratification                                                                                      | The budget is 2× measured Michigan-statewide values. Is this headroom appropriate, or should it be tighter?                                                                               |
| C   | ContradictionFieldSystem optimization approach                                                                       | The #1 tick-loop hotspot (182.6ms/tick @ 83 counties) scales super-linearly. Algorithmic investigation may require float-math reordering (R-PROOF). Approve the investigation?            |
| D   | National hex hydration optimization approach                                                                         | >10min for 3,156 counties. Batch QCEW/BEA lookups + parallelize. Approve?                                                                                                                 |
| E   | E:105 scope — given the national run can't complete yet, should E:105 be deferred until the optimization spec lands? | The national canonical acceptance is the program's capstone. Options: (a) defer E:105, (b) run a shorter national run (50 ticks), (c) optimize first then run.                            |
| F   | DeepSeek max-thinking directive                                                                                      | The "DeepSeek Thinking subagents with max thinking" directive was not honored by any dispatch (the task tool doesn't expose model selection). Is there a different way to configure this? |

## Updates 2026-07-07/08 (remediation program + spectrum)

- **Decisions C, D, E: RESOLVED** by the remediation-plan ratification (2026-07-07):
  Percy ruled FULL national perf effort — author spec-106 → profile FIRST → optimize
  → pass the 104 gate → run the 105 capstone. That approves the C investigation, the
  D optimization, and picks E option (c) optimize-first-then-run.
- **Item 22 (NEW, PENDING — the only live owner blocker): leaked Cloudflare API token.**
  `git push origin dev` blocked by GitHub push protection (token in
  `sessions/session-ses_0d18.md`, commit `c1cba41a`; verified the only secret in the
  unpushed range). Required: rotate at Cloudflare, then choose [A] unblock-URL push
  or [B] approved range-constrained filter-repo scrub. Details:
  `execution/PROGRESS_REPORT-2026-07-08.md` §9.
- **Item 23 (NEW, ✅ RULED 2026-07-08): the Spectrum of Unequal Exchange** (spec-107,
  Program 10). Five rulings: (1) ONE global axis, empirically anchored — "should
  reflect the actual data of the economy"; (2) wages ALIGN to position, don't define
  it; (3) first slice couples value-transfer-up-gradient + wage gravitation +
  consciousness; position mobility deferred; (4) spec now, implement as Phase 5.5
  (after 5.2/5.3), acceptance in the Phase-6 national capstone; (5) I-O grounding via
  loaded BEA TOTAL_REQ × QCEW (BLS EP optional cross-check). Master record:
  `programs/10-spectrum-of-unequal-exchange.md`.
- **Item 24 (NEW, ✅ RULED 2026-07-08 evening): the Transport Substrate** (spec-108,
  Program 11) — declared "the last thing we need" (final NEW feature). Rulings:
  (1) res-8 hexes are engine-only, NO visualization; (2) AI must construct new roads
  and repair; (3) primitive degradation mechanic required; (4) repair/reconstruct/
  rebuild after player attack / protest / riot; (5) slime-mold routing per
  Constitution II.13 + M1. Master record: `programs/11-transport-substrate.md`
  (verified inventory: spec-036 res-8 substrate BUILT but engine-orphaned; spec-063
  ships the min-cost-flow half; conductivity overlay + condition/degradation +
  BUILD/REPAIR verbs are the gap; HPMS/NTAD/FAF5 data present in trove).
  **4 open sub-questions for Percy in the master record §Open questions** (corridor
  ownership/tolls; informal slime-mold-only routes in slice 1?; BUILD/REPAIR as new
  ActionTypes?; waterways/ports in slice 1?) — none block spec authoring.
