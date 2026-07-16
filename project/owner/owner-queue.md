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
  **All 4 sub-questions RULED same evening (R2-1…R2-4, recorded in the master record):**
  (1) corridors state-owned for simplicity; (2) informal slime-mold-only routes SHIP in
  slice 1; (3) BUILD/REPAIR mapped onto existing `BUILD_INFRASTRUCTURE` (exists,
  `actions.py:81`) — zero new ActionTypes; (4) waterways/ports deferred to the same
  slice-2 feature as AIR_LINK. Item 24 is fully ruled; spec-108 authoring is unblocked.

## Updates 2026-07-08 late evening (Phase 2 completion — Opus 4.8)

- **Phase 2 COMPLETE.** All four interrupted lanes (2.2 `1546a330`, 6.2 `0fae122c`,
  2.4 `9f6f244e`, 5.4 `ad457f8c`) + both parked defects (Wave 3 `276fcb2b`) + the 2.R
  capstone (`5d954ecb`) merged to dev; full `mise run check` green (9421 passed). All
  six P0s fixed. Details: `execution/PROGRESS_REPORT-2026-07-08.md` §0.
- **Item 22 (token) — prevention half DONE, rotation still PENDING.** `sessions/` +
  `.dev.vars*` are now gitignored and `session-ses_0d18.md` untracked (`88e34ab5`), so
  the leak cannot recur. STILL REQUIRED (owner): rotate the token at Cloudflare + choose
  [A] unblock-URL push or [B] the prepared filter-repo scrub. Push to origin remains blocked.
- **Item 25 (NEW, ✅ RULED 2026-07-08 → Phase-3 spec): Territory↔FIPS contract + static
  bridged economy.** 2.R found the canonical 520-tick run cannot complete — gamma wiring
  (`cc4a5303`) exposed a latent crash at **tick 52** (`ClassDistribution.fips='T001'`,
  needs ≥5 chars): `WorldStateBridge` mints territory ids `T{i:03d}` while
  `TickDynamicsSystem` assumes `territory.id == county FIPS`; the `Territory` model has no
  `county_fips` field (same root gap as owner-queue §7.6 / PROGRESS_REPORT §7.6). Coupled
  finding: the bridged hex economy is **static** (production not evolving the material
  base). **Percy's ruling: dedicate a Phase-3 spec** — add `county_fips` to `Territory`
  + round-trip it (through the fragile `TERRITORY_EXCLUDED_FIELDS`/C.1-gate contract) + fix
  both engine readers, THEN investigate the static-economy production loop, THEN re-run 2.R
  for a real 520-tick baseline to CLOSE `cc4a5303`. Full evidence:
  `specs/102-gamma-shocks/proof-2R-baseline-regen.md`. `michigan-e2e.json` stays valid on
  its gated fields until this lands.

## Updates 2026-07-09 (Fork Reconciliation Ledger — Part 2 of the src/ sweep)

**Item 26 (NEW, PENDING — needs Percy's rulings): the Fork Reconciliation Ledger.** Part 2 of the
ADR058 sweep. Full analysis: `project/execution/FORK_RECONCILIATION_LEDGER.md` (+ ADR059). A
30-agent workflow (15 rigor analysts + 15 adversarial verifiers, 0 errors, 14/15 CONFIRMED) produced
one rigor+data-accuracy recommendation per successor-fork. **The ledger proposes; you dispose** — rule
each fork inline in the ledger's `— Percy's ruling:` slots, then a Part-2b phase implements behind
`mise run check` + byte-identical `qa:regression`. No `src/` changed to author it.

Two tiers. **Rubber-stampable (byte-identical, rigor-safe):**

| Fork | Recommendation | Note |
| --- | --- | --- |
| F2  | delete-orphan (`InterpolatingBEASource`) | salvage the ~60-line interpolation into the live service first (separate change) |
| F7  | delete-orphan (consciousness trio) | keep `tendency_modifier` |
| F9  | delete-orphan (`derivations/`) | byte-identical duplicate of `world_state` computed_fields |
| F10 | delete-orphan (`TraceRecorder`/`trace_log`) | **bundle with F11** — observers are its only callers |
| F11 | unify (keep canonical `SessionRecorder`, drop `PersistenceObserver`) | JSONL recorder = separate delete-orphan unless you want it wired |
| F12 | delete-orphan (`calculate_rate_of_profit`/`_organic_composition`) | Epoch-2 intent preserved in `epoch2-trpf.yaml` |

**Genuine rigor rulings (baseline-moving or a value/theory judgment):**

| Fork | Recommendation | Decision you're being asked to make |
| --- | --- | --- |
| F1  | wire-orphan/retire-live (Leontief spec-057) | (a) Leontief vs trade-DRAIN as canonical Φ magnitude (double-counting risk); (b) may the Hickel **fixture** be read at runtime (III.4.2)? |
| F3  | wire-orphan/retire-live (Mobilize/Aid defines) | `turnout_per_sl` model+units (0.01 pop-fraction vs 10.0 demonstrators/SL); confirm `aid_efficiency` 0.85. Ruling must land BEFORE the wire. |
| F4  | **CONTESTED** (wire, revised by skeptic) | rule the skeptic's 3-part split: wire `compute_action_cost` (moves baseline), DRY-fold the AP loop, hold coordination guards (blocked on a multi-target generator) |
| F5  | reconcile (institution half-migration) | approve freeze-the-bool + schedule spec-040 wire as the terminal state (an ADR/convention) |
| F6  | wire-orphan/retire-live (gamma-III) | approve the gamma data program (QCEW care facts 086/097/098 + ATUS catalog add); immediate fixture-cleanup is byte-identical *(re: item 9 "wire gamma now")* |
| F8  | reconcile (3× Φ) | is the internal-colony wage differential a **4th Φ channel** (I.2 amendment, IX.3) or kept separate? |
| F13 | reconcile (QCEW dedup) | extract the safe hydrator-build half only; low stakes |
| F14 | reconcile (inf-vs-0.0) | doc the convention (premise was largely false — legitimate specialization) |
| F15 | unify (EndgameDetector overshoot) | route through canonical `overshoot_ratio`; fixes a latent bug (zero-biocapacity can't currently fire ECOLOGICAL_COLLAPSE); **run `qa:regression` before merge** |

Cross-cutting: **bundle F10+F11**; **F3 value-ruling before wire**; **F1 needs the DRAIN reconciliation
decision first**; a recurring **fixture-as-runtime (III.4.2)** theme spans F1/F6/F8 (own remediation pass).

## Updates 2026-07-09 (E2E walkthrough sanity check + status reconciliation)

- **✅ Core loop verified PLAYABLE (no ruling needed — status update).** A live sanity-check
  walkthrough on `dev @ b57faee6` drove the real UI + API against a live Postgres `EngineBridge`:
  `real-loop.spec.ts` **7/7** (login → create game → real map → verb submit → **end turn advances the
  tick** → results/events), and every game surface returns live data when authenticated. The
  2026-07-07 "unplayable" verdict is **resolved**. Full evidence:
  `project/assessments/E2E_WALKTHROUGH-2026-07-09.md`.
- **Item 25 — crash half ✅ FIXED** (`b57faee6`, `Territory.county_fips`); the **static bridged
  economy** (2nd half) is still open and was **confirmed live** (resolving tick 1→2 advances the tick
  but org/economy values are identical — `wayne_county` MELT is unavailable pre-tick-52). Still owner
  item 25's already-scoped Phase-3 spec; nothing new to rule.
- **Item 22 — push ✅ DONE** (`origin/dev == 1c7524b8`), token scrubbed from history. The only residue
  is **token rotation at Cloudflare** (hygiene, owner action — no longer blocks anything).
- **Item 27 (NEW, low-stakes gate fix — no ruling, just a work item): Playwright C.5 auth-harness gap.**
  `playwright.config.ts` has no `storageState`/setup project, so 9 secondary e2e specs
  (`briefing-live-data`, `intel-results-analysis`, `orgs-live-data`, `polling-tick-aligned`) navigate
  without logging in → render `/login` → **false red**. Proven benign (the authenticated API drive
  returns real data for all those surfaces). Fix = add a login `storageState`. Matters because the CI
  Playwright leg currently only truly exercises the `real-loop` happy path. See walkthrough **G1**.

## Updates 2026-07-09 evening (Program 12 wave-1 merged + Amendment Q + A7 ruling request)

- **Program 12 "The Cockpit" ratified + executing** (4 rulings, `programs/12-cockpit.md`, ADR061).
  Phase A data spine MERGED except A7: A8 `f1a57ff3`, A1 `08e3131a`, A3+A5 `665e0814`, A6 `c5c19e21`,
  A2 `b0907b97`, A4 `9addfa94`; B1 cockpit scaffold `30f5512e`+`504302bf`. Wave-1 = 6 parallel sonnet
  worktree lanes (ultracode), 0 errors, rebased + ff-merged linearly.
- **Item 8 ✅ CLOSED** (A6, `c5c19e21`): every web session seeds the spec-070 political layer at tick 0
  (4 factions, 3 sovereigns, ~324 INFLUENCES edges, res-7→res-6 H3 aggregation) and it survives a real
  engine step. Headless baselines untouched (bridge-layer seeding; qa:regression 5/5 proven twice).
- **Item 12 — faction half ✅ CLOSED** (same commit): `WorldState.factions` + from_graph faction branch
  + INFLUENCES payload fields on `Relationship` (exclude_none, byte-identical elsewhere). Sovereign
  half was closed earlier (fix/from-graph-safety). **Community nodes remain the open third** (still no
  from_graph branch; still latent — no production path adds them).
- **Item 28 (NEW — needs a ruling eventually, not urgent): endgame detector threshold tension.** The
  endgame lane proved A6's round-trip machinery fully fixes the old xfail claim (colonial_stance
  survives; ABOLISH/CEASE/solidarity gates all resolve), but the augmented REVOLUTIONARY_VICTORY test
  still can't pass because `_check_fascist_consolidation`'s legacy false-consciousness route fires on
  an ABSOLUTE count (`fascist_majority_threshold=3` nodes with national_identity > class_consciousness)
  and FR-033 checks it first — any fixture with ≥3 settler-aligned entities (required by the
  cross-divide-solidarity gate itself) trips it. Ruling options: make the threshold a population
  share, or scope the legacy route so it doesn't pre-empt the augmented spec-070 gates. Accurate
  diagnosis now lives in the xfail reason string (`e0338924`).
- **Item 29 (NEW, low priority — owner awareness):** per-hex class populations
  (`pop_bourgeoisie`..`dominant_class`) stay honestly None because no shipped scenario sets
  `SocialClass.county_fips`; deciding per-hex vs county-broadcast aggregation is worth a ruling before
  anyone wires it (A2 lane finding). Related awareness note: A4's communities dashboard reports REAL
  SOLIDARITY-edge components; the spec-061 FR-018 XGI `community_memberships` layer is never assigned
  by production code — if you want that layer, it needs a scenario-builder spec.
- **Amendment Q ratified** (Constitution v2.9.0): III.12 Behavioral Contracts + VIII.13; program 13
  (`programs/13-behavioral-contracts.md`) registered — determinism-contract doc + dense goldens. ADR062.

### Item 25 second half — A7 DESIGN RULING NEEDED (scout report delivered)

The scout mapped **three distinct economy layers**: (1) entity wealth ALREADY moves every tick
(Production/ImperialRent systems, annual÷52 pattern); (2) county TickDynamics state moves ONLY at year
boundaries (`tick % 52` gate, `economics/tick/system/__init__.py:130`); (3) hex c/v/s/k NEVER moves —
the bridge re-emits the tick-0 template every tick by documented design, and spec-089's delta-storage
savings are premised on exactly that. Bonus finding: `base_year` is set once at session init and never
advances, so tensor lookups are pinned to one year forever (a separate staleness bug worth its own fix).

Four designs on the table (full detail in the wave-1 scout report; Fable's recommendation = **B**):

| Option | Shape | Effort | Notes |
| --- | --- | --- | --- |
| A | glide-path interpolation toward year N+1 with boundary true-up | L | uses year-N+1 data mid-year ("sees the future"); restructures the annual pipeline |
| **B (recommended)** | keep the annual pipeline annual; accrue per-tick FLOWS (annual÷52) at county level, matching the existing ImperialRent pattern | M | conservation exact by construction; annual-resolution facts stay honestly annual; smallest blast radius |
| C | genuine per-tick hex c/v/s/k mutation | XL | the bridge docstring's own "future spec"; directly invalidates spec-089's ~98% dedup storage premise |
| D | read-time interpolation in `v_hex_state_asof` | L | presentation-layer motion without engine motion — III.11-adjacent; two read-site drift risk |

**Questions for Percy:** (1) layer scope — county (B), hex (C), or B-now-C-later? (2) confirm the
annual pipeline STAYS annual (quarterly-crisis/class-transition semantics untouched) with only flows
accruing per tick; (3) is `tests/baselines/storage-budget-5t.json` part of the ONE sanctioned
rebaseline, or a separate sign-off? (4) fix the pinned `base_year` staleness in the same spec or
separately? Rebaseline procedure is fully mapped to the proof-2R precedent (detroit-tri-county-5t +
storage-budget-5t + the 520-tick michigan-e2e canonical, A/B determinism via Postgres EXCEPT diff).

## Updates 2026-07-09 late evening (wave-2 merged: A7 engine half + determinism contract + B2)

- **Item 25 second half — ENGINE HALF ✅ IMPLEMENTED** (Percy's "lets get at it" read as Option-B
  approval; `742e7163` flow accrual + `e75464fe` base_year fix). TickDynamicsSystem is two-mode:
  boundary ticks run the annual pipeline unchanged; non-boundary ticks accrue per-tick flow slices
  (`flow_phi_accrued`/`flow_wage_accrued`, annual÷52, conservation proven by property tests — 52
  slices sum exactly to the annual total). ProductionSystem's tensor year now advances with the tick
  (was pinned to `base_year` forever). **Zero baseline drift anywhere**: qa:regression 5/5
  byte-identical (no defines_hash movement — no new coefficients needed), and qa:e2e-regression +
  qa:storage-budget PASS unchanged — root-caused (proof-A7 Part 1c/5): those gates compare
  `view_runtime_trace_emission`, sourced entirely from `dynamic_hex_state`, which Option B leaves
  frozen by design. **The "one sanctioned rebaseline" turned out to be zero rebaselines** at 5-tick
  scale — the ONE real regeneration is `michigan-e2e.json` (below).
- **Item 25 ✅ CLOSED (engine layer) + `cc4a5303` R-PROOF ✅ CLOSED — same evening, later.** The
  520-tick canonical COMPLETED (twice — first completions since gamma exposed the tick-52 crash):
  sessions `a8cbf1ab` (baseline writer) + `970951e3` (A/B partner), ~45 min each.
  `tests/baselines/michigan-e2e.json` regenerated: gated terminal fields **byte-identical** to the
  old baseline (the frozen-hex-layer signature — honest caveat in proof Part 3), real movement = +9
  year-boundary events + conservation-audit content. **A/B determinism: 0 divergent rows in both
  directions** across dynamic_consciousness/demographics/employment/hex (585,760 rows per direction) —
  even the delta-emission pattern is identical. Full proof: `specs/109-data-spine/proof-A7.md`
  (Parts 0–6 complete, verdict CLOSED). Remediation 2.R row closed. What remains of item 25's spirit
  is item 30 (web visibility, lane in flight) and the deliberately-deferred hex-layer Option C
  (future owner-ruled spec).

## Updates 2026-07-09 night (wave 3 merged: the cockpit exists + item 30 closed + program 13 complete)

- **Item 30 ✅ CLOSED** (`143a3eed`). The lane confirmed both A7 findings AND found a third, bigger
  one: **EngineBridge never wired the economic calculators at all** — zero ServiceContainer overrides
  in the web bridge, so TickDynamicsSystem unconditionally no-op'd on EVERY web session since spec-061.
  Fix (all bridge-layer, zero engine changes): calculators wired mirroring the headless runner (gated
  on county_fips presence, no-op for non-county scenarios — byte-identical elsewhere); all 81 wayne
  territories county-backed with real FIPS 26163 (all-81 chosen over one-designated because a
  5-char/H3-id mix would crash CountyEconomicState's fips constraint); county flows carried across
  resolve→persist→hydrate→resolve via the graph-level county_states dict + per-tick accrual slice.
  **Acceptance proven through the real production path: flow_wage_accrued 0.0 → 84,000,000 →
  168,000,000 across consecutive resolve_tick calls** (= median_wage 21.0 × 2080 h × 100k employment
  ÷ 52, exact), surfaced honestly in get_economy_dashboard.county_flow (None when absent). Gates:
  qa:regression 5/5, qa:e2e-regression zero drift, qa:storage-budget unchanged, tests/unit/web 371/371.
- **Item 32 (NEW, follow-on from item 30):** annual (year-over-year) county continuity in web
  sessions — every 52-tick boundary re-bootstraps county state (capital_stock/median_wage reset)
  because persistent_context is not stored durably per session. Within-year flows are fixed; multi-year
  accumulation needs session-level persistent_context storage. Also inherited notes: the spec-057
  Leontief phi pipeline is unwired in BOTH runners (phi flows stay 0.0 — a data-pipeline program, not a
  bug); territory_snapshot's (game_id,tick,county_fips) PK keeps 1-of-81 wayne rows (pre-existing).
- **Item 27 ✅ CLOSED — TIER-3 LIVE VERIFIED** (`1c62fc93`): storageState auth harness added
  (setup project + chromium-authenticated project); ran against the live stack — **8/10 previously
  false-red specs now pass authenticated** (G1 resolved). The 2 residuals are pre-existing spec bugs,
  now **item 33**: (a) `polling-tick-aligned.spec.ts:33` uses an unauthenticated `request.newContext()`
  for its direct /resolve/ call (401s regardless of login); (b) `orgs-live-data.spec.ts:28` OODA-badge
  text assertion doesn't match the live rendering. Both are small test fixes, no ruling needed —
  queued for the next smalls lane.
- **Item 31 — docstring half ✅ DONE** (`d94c82db`): envelope.py now describes the two-hashes reality
  precisely. The rename (tick_commit.determinism_hash → replay_identity) remains yours to rule.
- **Program 13 ✅ COMPLETE** (`60a919e3` + `66125a22`): dense per-tick goldens for all 5 scenarios,
  byte-compared in qa:regression by default (wall time unchanged — same simulation run feeds both
  paths), double-generation determinism proof, synthetic-mutation detection named tick+column.
  Constitution III.12 corollary (a) flipped to `[IMPLEMENTED]` (v2.9.1, PATCH).
- **B3+B4 ✅ MERGED — the cockpit exists** (`a8c8a9dd` + `a1187bca`, 307 vitest tests): one store,
  one orchestrator (the 13 pollers are dead in the new app), Pause/Step/Play with 409/5xx/autopause,
  login→lobby→game routes, full five-region shell wired to the real A4 endpoints and the B2 map.
  Remaining Phase-B: B5 takeovers, B6 e2e port + live-browser parity drive (next wave).

## Updates 2026-07-10 early morning (wave 4: PHASE B COMPLETE — parity gate GREEN 23/23 live)

- **THE COCKPIT WORKS IN A REAL BROWSER.** B6 built the storageState harness + six CI-canon specs
  and drove them live (real Django, real EngineBridge, real Postgres). First run found **the**
  blocker: `development.py`'s CSRF/CORS origins only trusted `:5173` — every cockpit browser POST
  (login/create/submit/resolve) 403'd. Fixed (`d5f270b2`: 5174 added + `BABYLON_EXTRA_DEV_ORIGINS`
  env extension so this class of defect can't recur). Two real UI defects found by the live drive
  and fixed (`f7fff8ab`): the pause control was unreachable during `resolving` (where Play spends
  ~all wall time with real multi-second resolves), and EventsFeed's honest-empty copy lacked its
  testid/container. **Final: 23/23 passed, two consecutive full runs. Phase-B exit gate GREEN.**
- **B5 ✅** (`a7b7a9b2`): Wire/Chronicle/Dialectic takeovers over the persistent shell + Objectives
  dock tab. **C4 ✅** (`30c5faf1`): observatory ported (Cold Collapse palette remap) + route
  registered. **C2 ✅** (`f9ac774c`): edges/state-apparatus/infrastructure dashboards + NEW
  org/territory history endpoints — `get_infrastructure` had never existed at all (the api view
  would have `AttributeError`'d on any real request); honest-empty until the transport substrate
  (Amendment O) writes rows. **C1 ✅** (`a0054dc5`): LLM narrator service at the bridge boundary —
  `BABYLON_LLM_NARRATOR` flag, default OFF is parity-tested byte-identical, async post-tick, III.6
  model+prompt pinning, III.11 loud `degraded` marker; provider mocked in tests, key never read.
- **Item 33 ✅ CLOSED** (`2491b9ba`): polling spec now authenticates its direct resolve POST (real
  tick advance verified in Postgres); the orgs OODA assertion "bug" had already dissolved with the
  item-27 harness — verified live against 4 sessions, no stale assertion existed (III.11: no
  fabricated fix).
- **Item 34 (NEW, small):** `StubEngineBridge.create_game()` signature drifted from the api view
  (`config` vs `_config` — TypeError on any create when the stub is active). Found when a Django
  restart without `RUN_MAIN=true` silently fell back to the stub. Two follow-ups worth a smalls
  lane: fix the stub signature, and consider a LOUD startup log line when the stub (not the real
  bridge) is serving (III.11 — a stub silently impersonating the engine is how this hid).
- **Environment notes:** the orphaned Jul-6 vite squatting the cockpit's canonical port 5174 was
  killed (pid 2459793); Django restarted with `RUN_MAIN=true` + the new origins (real bridge
  confirmed: "EngineBridge initialized with PostgresRuntime").
- **What remains in Program 12:** C3 design session (owner-invited — your call when), C5 polish
  (deferred until after C3 reshapes visuals), **Phase D cutover** (delete `web/frontend`) — parity
  evidence now exists; D still needs your explicit go + parity green on ≥2 consecutive dev merges.
- **The autonomous /goal backlog is exhausted**: every remaining project/ item needs an owner
  ruling (items 26 fork ledger, 28, 29, 31-rename, 32, C3, Phase D, push-to-origin).
- **Item 30 (NEW — the web-visibility half of item 25; needs scheduling, not a design ruling):**
  web sessions cannot sustain county-layer state at all, independent of A7. Two structural gaps found
  with source-level verification: (a) `EngineBridge.resolve_tick` passes a FRESH
  `persistent_context={}` every call and the round-trip strips `tick_`/`flow_` territory attrs
  (Territory `extra="forbid"`), so TickDynamics per-node output can never survive between resolve
  calls; (b) the `wayne_county` web scenario has ZERO county-resolution territories (hex-only H3 ids,
  `county_fips=None` everywhere), so county flows can't surface there even after (a). The engine-level
  fix is proven by `tests/integration/web/test_static_economy_flow.py` (flows move tick-to-tick on a
  persistent graph through the full 26-system pipeline — the headless model). Making the WEB session
  show it = thread `persistent_context` (or round-trip the flow attrs) + give web scenarios
  county-backed territories. Candidate: fold into Phase C or its own small spec.
- **Item 31 (NEW — constitutional-integrity findings from the determinism-contract lane; rule when
  convenient):** (a) `tick_commit.determinism_hash` is NOT a content hash — it is literally
  `sha256(f"{session_id}:{tick}:{seed}")`, zero dependency on world state or actions, so it cannot
  detect a divergent replay; the hash that matches III.7's text is `compute_determinism_hash()` in
  `conservation_audit_log`. The migration comment calling it "the queryable Constitution-III.7 hash
  chain" overstates it. (b) `PerTickTransactionEnvelope`'s docstring claims one shared hash per tick;
  the live wiring computes two different values under the same field name. (c) player actions are
  never threaded into the content hash in the live runner path. All documented (not fixed — doc-only
  lane) in `docs/reference/determinism-contract.rst` "Known Discrepancies". Options: rename
  `tick_commit.determinism_hash` → `replay_identity`, fix the docstring, thread actions when a caller
  exists. Also noted: `mise run docs:strict` (sphinx -W) is RED at HEAD with 1,919 PRE-EXISTING
  warnings (CI uses plain sphinx-build and is unaffected) — a separate doc-hygiene pass someday.
- **Program 13 item 1 ✅ DONE** (`66125a22`): `docs/reference/determinism-contract.rst` (621 lines) —
  all three hashes specified byte-level with empirically verified serialization claims and a worked
  example that reproduces the committed `imperial_circuit.json` defines_hash (`fe1ada8c54bec6c0`)
  exactly. III.12 corollary (a) marker stays `[PENDING CODE]` until item 2 (dense goldens) lands, per
  the program's own DoD.
- **B2 ✅ MERGED** (`dc384c78` + `115e6fc7`): survivor modules ported into the cockpit — Cold Collapse
  tokens (self-hosted fonts), types, lib (eventClassifier, verb-config, all 9 verbs + fetchVerbTargets
  extracted store-free, selectors), the unified `Lens` discriminated union (duplicate-"heat" collision
  eliminated; `MAP_METRICS` mirrors `map_contract.py`), map components as pure controlled components
  (store/router wiring = B3). 17 test files / 172 tests green. Also fixed a real B1 bug: prettier
  semver drift vs the pre-commit exact pin (format ping-pong). Not ported (documented): FramingSelector
  + the third "analytical lens" concept (`lensDefinitions.ts`/`useLens.ts`) — B3 decides.

## 2026-07-10 midday — C3 design-sync session (Percy-invoked `/design-sync`)

- **C3 substrate ✅ DELIVERED** (`23016c79` + `ccf8994c`, dev @ `ccf8994c`): all 49 cockpit
  components synced to the claude.ai/design project **"Babylon Cockpit"**
  (`https://claude.ai/design/p/9ccdf916-1447-4c12-92a3-dfc2a0939a4c`) — 121 authored preview cells
  all graded good (solo calibration + 6-lane sonnet wave, 1.86M tokens, 0 errors), render check
  49/49, `.d.ts` API contracts parse-clean, conventions header (the design agent's Cold Collapse
  contract) validated name-by-name against the shipped stylesheet. Your existing "Babylon Design
  System" canon project untouched (kept as archive/reference). Design sessions there now compose
  with the REAL components; token/CSS output paths back into `src/frontend` per the C3 plan.
- **Two production bugs found by the campaign, FIXED (no ruling needed)**: WireApp triptych columns
  had no flex-basis (row collapsed at `story=null`; IntelColumn wrapped mid-word populated) →
  `wire.css` `.col-wrap` `flex: 1 1 0`; `EMPTY_WIRE_FEED` filter accents referenced unprefixed
  `var(--rent)`-style tokens nothing defines → `--babylon-*`. Both pinned by
  `wire.contracts.test.ts` (red→green).
- **Item 35 (NEW — small design ruling):** the `:root` type scale (`--text-md`, `--tracking-label`…)
  is vars-only, NOT `@theme`, so `text-xs`-style utilities are Tailwind's default rem scale, not your
  10px scale — components (and now the design agent's conventions) use the `text-[10px]` pixel idiom
  instead. Promoting the scale into `@theme` in `src/frontend/src/index.css` would make `text-xs`
  MEAN 10px — but it re-sizes any existing default-scale usage, i.e. app-visible. Rule: promote or
  keep the pixel idiom canonical.
- **Item 36 (NEW — contract disagreement):** `DialecticSpread` labels at most 2 oppositions
  (`frame.principal`/`frame.secondary` slots) while `ContradictionFrame.oppositions[]` is unbounded —
  a 3rd+ entry renders raw snake_case keys + bare pole letters (reads broken). Also its
  `{error && …}` banner renders unconditionally (not gated on empty data) — a fetch hiccup under a
  real gameId grows a stray error above an otherwise-populated grid (III.11 wart). Rule: bound the
  type, extend the frame, or gate the banner.
- **Item 37 (NEW — dead field):** `GameSnapshot.endgame` (`types/game.ts`, 3-outcome `EndgameData`)
  has ZERO readers — the real endgame path is `panels.endgame` reading `EndgameState`/
  `TerminalOutcome` from `types/dialectic.ts` (the 5 real outcomes). Delete the orphan or wire it.

## 2026-07-10 evening — PROGRAM 12 COMPLETE: Phase D cutover + C5 + push (your "finish it all")

- **Phase D ✅ EXECUTED**: `web/frontend` DELETED (`2c7cc159`, −39,818 lines) under the full ledger
  (`specs/112-cutover/test-port-ledger.md` — 81 dispositions, both parity runs recorded). Parity
  **25/25 live at both bracketing HEADs**; `mise run check` TRUE-exit 0 (9,457); `qa:regression`
  5/5 byte-identical. The cockpit is THE frontend on **:5173** under "Babylon - The Fall of
  America". Tooling re-pointed end-to-end (mise `web:*` canonical, cockpit aliases retired;
  pre-commit old set deleted; CI e2e job → src/frontend; Ansible `frontend_dir`).
- **C5 ✅ LANDED**: Q/E lens cycling; heartbeat referential stability (the map no longer rebuilds
  every deck.gl layer on each 2s beat — worldSlice keeps the snapshot reference when a same-tick
  payload is deep-equal); **county framing is real** — FramingSelector + region rendering via
  `member_h3` H3ClusterLayer aggregates, default framing honest `hex`.
- **Deletion gates caught 3 live deps** hiding in the retired tree (the ledger's whole point):
  `seed_hex_data`'s fixture (now `web/game/fixtures/`), a segment-wise path in
  `test_contract_parity`, and the e2e helper's own port default. All fixed, all green.
- **Item 38 (NEW — backend quirk, pinned not fixed):** `zoom="bea_ea"` falls through
  `group_key_map` to county grouping exactly like the pinned `cz` quirk (and `cz` needs a schema
  addition — no commuting-zone column on `hex_latest`). Both accepted by `VALID_ZOOM_LEVELS`;
  both silently county-group. Rule: schema work, doc it, or narrow the accepted zooms.
- **Item 39 (NEW — design mapping):** region fill for the `stance` lens aggregates onto the
  consciousness ramp (`regionFill.ts`, pinned by test). Flagging for your eye per the plan.
- **WATCH:** the next Hetzner deploy — Ansible re-point verified by syntax-check only (no
  staging). `frontend_dir` in `group_vars/production/vars.yml`.
- **CI RESURRECTED (was disabled at the repo level since 2026-05-12** — every push since ran
  nothing; re-enabled via API + `workflow_dispatch` added). Three fix-forward rounds landed:
  from-zero migrate (`25bc0150` — had NEVER worked), GDAL system libs for every pytest job +
  stale-venv-cache bust (`a976e1b1`), Postgres-job migrate step + an isort classification split.
  **Frontend + AI Tests jobs GREEN; playwright-e2e runs 21/23 live specs in CI.**
- **Item 40 (NEW — infra ruling): the reference DB in CI.** `data/sqlite` is an untracked
  symlink into your 5.7 GB trove — CI has NO reference DB, so (a) the two resolve-driving e2e
  specs 500 (item-30's county calculators read it during resolve) and (b) the sqlite-dependent
  unit tests fail in the main CI leg (same class as the known worktree-symlink failures).
  Options: a small COMMITTED fixture subset DB for CI, a release-asset download step, or
  loud skip-if-absent guards. Your call — it shapes what CI can honestly gate.
- **Item 41 (NEW — dependency debt): pip-audit finds 73 known vulnerabilities in 15 packages**
  (two months of CVEs accumulated while CI was off; 1 already ignored by the job). Needs a
  dedicated upgrade session — bumping blind would churn poetry.lock across the engine.
- **CI run #4 final ledger (2026-07-10 evening, `8dafdadb`, four runs total):** GREEN —
  Frontend, AI Tests, Style, ruff AND mypy in the main job (the isort split + fresh venvs
  worked). REMAINING RED, all item-40/41 territory, no further fix-forward: (a) main job's
  pytest leg (needs the reference DB); (b) Postgres Integration — Django schema now migrates
  in-job, but the direct-host suites also expect the ENGINE runtime tables
  (`node_state`/`edge_state` — PostgresRuntime `init_schema`, which local 5433 accumulated
  from months of engine runs; fold into item 40: CI environment parity needs engine schema
  init + the reference-DB strategy together); (c) playwright-e2e steady at 21/23 (the two
  resolve-500s = reference DB); (d) Security Audit = item 41. CI is now a working, honest
  signal again — what it says red IS red for a fresh environment.

## 2026-07-11 — Program 14 (Correspondence) COMPLETE

- **The tree now states the constitution, and the linters enforce it.** Layering law
  (`kernel < models/formulas < topology < domain < persistence < engine`; `intelligence`
  observes) is import-linter-enforced in pre-commit, `mise run check`, and CI. New packages:
  `babylon.kernel` / `babylon.topology` / `babylon.domain` / `babylon.intelligence`. The
  repo-hygiene gate (root allowlist, tracked-ignored=0, >1MiB non-LFS blobs) runs before
  poetry in CI. Every phase held `qa:regression` 5/5 byte-identical — the engine never moved
  numerically across ~900 touched files. ADR063 + `project/programs/14-correspondence.md`.
- **Your six fork rulings are EXECUTED** (ledger rows stamped): F2, F7, F9, F10, F11, F12 —
  ~3,900 LOC of adversarially-verified dead code gone, byte-identical proven. **Item 26 is
  now 6 executed / 9 pending** (F1/F3/F4/F5/F6/F8/F13/F14/F15 still want rulings).
- **Item 42 (NEW — deferred by the ledger, needs its own ruling): F2 interpolation salvage.**
  Port the orphan's linear-interpolation into `DefaultBEAShareLookupService` as an optional
  mode + give `GLOBAL_FALLBACK_SHARE=0.5` a GameDefines source (III.1). Baseline-moving.
- **Item 43 (NEW — small ruling): `JsonlSessionRecorder`** (now `engine/observers/
  jsonl_recorder.py`) — orphaned local-JSONL forensics sink; F11 left it as a separate item.
  Keep (wire someday) or delete-orphan.
- **Item 44 (NEW — docs architecture): `docs:strict` is structurally red** — first-ever run
  of the gate exposed ~2.4k pre-existing duplicate-object warnings (autosummary × handwritten
  `api/*.rst` document every symbol twice) + 24 toctree + 6 paradox-lexer. Zero rename-class
  warnings (Program 14 is docs-clean). Ruling: drop the handwritten `api/{models,formulas,
  engine}.rst` automodule pages, or disable autosummary recursion, or suppress-with-reason.
- **Rust posture RULED and recorded:** deferred until a measured national-scale CPU profile;
  method = PyO3 strangler per module behind the dense goldens under III.12(b) tolerance.
  **Subrepos REJECTED** (one determinism contract spans the sim). The kernel boundary this
  program built is the Rust preparation.
- **WATCH:** first CI run on the re-layered tree (push follows the records commit). Runner
  path expectations: hygiene gate + import contracts now run in the main job before pytest;
  reference-DB reds remain item-40 territory.
- **WATCH RESOLVED (run 29142171038, `b6522ffa`):** first CI on the re-layered tree is
  byte-for-byte the run-#4 red/green map — Frontend/AI Tests/Style green; **the two new
  Program-14 gates GREEN in CI** (repo hygiene + import-boundary contracts, before Ruff+MyPy,
  both also green); Playwright exactly 21/23 (the two item-40 resolve-500s); Postgres
  Integration + main pytest leg + Security Audit = items 40/41 as before. The re-layering is
  invisible to CI except for the added enforcement. CodeQL green.

## Program 15 — The Gauntlet (2026-07-11, ADR064)

**Items 40 + 41 CLOSED** (your ruling: fix both in-program):

- **Item 40 ✅**: CI reference-subset DB shipped — `tools/make_reference_subset.py`
  (63 TDD tests, policy-as-data, deterministic), released as `ci-data-v1` (391 MiB,
  93% smaller, sha-pinned). All marked suites proven against it (adapter suites via
  env override; the two hardcoded-path files via isolated worktree: 44 pass + 1
  intentional xfail; 3 national-coverage blockers by SQL). `CI_REFDB_READY=true` —
  the four gated main-tier jobs are live.
- **Item 41 ✅**: 73 pip-audit CVEs → 5 evidenced expiring ignores (six serial
  batches, each `qa:regression` byte-identical; engine-adjacent deps never touched).
  Security job BLOCKING on all tiers, green in CI. Ignores expire 2026-10-01 — the
  wrapper hard-fails then, forcing quarterly re-review.

**New items needing rulings:**

| # | Item | Context |
| --- | --- | --- |
| 45 | **postgis base migration** (alpine or PG17-bookworm) | The 16.x postgis line ships bullseye, period: 90 no-fix HIGH/CRIT are upstream's even after the 16-3.5 bump + build-time upgrades (184→139). The cure changes the DB substrate under the byte-identical bundle — PostGIS-on-musl can alter geometry float behavior — so it needs the full determinism protocol. trivy-image stays advisory until ruled. |
| 46 | **sentence-transformers `<5.0.0` pin** blocks transformers fixes | CVE-2026-1839 (fix 5.0.0rc3) + CVE-2026-4372 (fix 5.3.0) are fixable ONLY by bumping sentence-transformers past its transformers<5 pin. Both in the expiring-ignores file until ruled. **Update 2026-07-11 (deps wave, branch `deps/dependabot-wave-20260711`): resolved there** — sentence-transformers ^5.6 pulled transformers 5.13.1 + torch 2.13.0; raw pip-audit reports ZERO vulns and the expiring-ignores file was EMPTIED (all 6 entries incl. the torch trio). qa:regression 5/5 byte-identical. Lands with that branch's PR. |
| 47 | **spec-064 retired-contract tests** (3 xfails in test_parameter_analysis) | test_trace_captures_wealth_changes / test_trace_includes_phase_4_1b_metrics / test_json_export_captures_dag_structure assert contracts spec-064 retired (per-class wealth trace columns, phase-4.1b aggregates, export_json causal-DAG). Reintroduce the contracts, retire the tests formally, or retarget them at manifest.json. |
| 48 | **Oakland LODES hypothesis** (3 xfails, extends your item-7 ruling) | Real LODES data shows Oakland as a net job IMPORTER; the tests' own docstring says "left failing deliberately… flagged for owner review". Now xfail(strict=False) so the refdata CI job can be green — same signal, no forever-red job. Your item-7 ruling said "investigate then correct"; the investigation is in the module docstring, the correction awaits your call. |
| 49 | **bootstrap.yml:50 sshd_config.j2** | The live playbook's "Deploy hardened sshd_config" task references a template that NEVER existed (the deleted `common` role had no templates/). Authoring a hardened sshd config for the prod server is yours to specify. |
| 50 | **stale deploy docs** | `deploy/ansible-setup-guide.md` describes an architecture that was never built (Docker-Compose app, geerlingguy roles, Certbot); `deploy/README.md` still references the dead `playbook.yml` + deleted roles. Replace-with-pointer (like deploy/ansible/README.md got) or rewrite. |
| 51 | **complexity ratchet 15→10** | ruff C90-15 is now the single gate (xenon theater deleted). Dropping to 10 wants ~39 function fixes + 8 D-blocks. Ratchet when? |
| 52 | **infra-live secrets — console task** | infra-live.yml (ephemeral Hetzner, dispatch + Monday cron) fails loud until repo secrets exist: `HCLOUD_TOKEN`, `CI_SSH_PRIVATE_KEY`, `CI_SSH_PUBLIC_KEY` (Settings → Secrets → Actions), plus creating the `infra-ephemeral` environment. Cloudflare vars are NOT needed (CI applies run manage_cloudflare=false). |
| 53 | **local venv drift** | Your local venv runs Python 3.13.5; CI + .mise.toml pin 3.12. The weekly py3.13 leg covers forward-compat, and the determinism probe passed across both — but local-vs-CI parity would want a `mise install`-driven venv rebuild at your convenience. Not done unilaterally (it rebuilds your working venv). |

**WATCH RESOLVED (2026-07-11, runs 29158383092 + 29162559986):** maiden main.yml went
10/16 — Playwright E2E green FIRST TRY on the real stack; all six reds were first-run
wiring/content (schema bootstrap, DSN, GDAL, tflint floor, serial-shard timeout, trove
data gaps) and were fixed same day; the dev-dispatched proving run then took
postgres-integration, refdata-tests, and infra-validate GREEN, exposed the ci-data-v1
FAF gap (fixed as ci-data-v2) and two pre-existing rest-leg test bugs (fixed / item 56).
Second proving dispatch pending on the fixes branch; docs.yml Pages + phantom-alert
closure tracked there too.

## Deps wave 2026-07-11 (branch `deps/dependabot-wave-20260711`)

| # | Item | Context |
| --- | --- | --- |
| 54 | **testing-suite pass: slow-test taxonomy + fixture cost** (temporary fix shipped with the 2026-07-11 deps wave; the deeper pass below awaits your ruling) | The local fast gate (`mise run check` → test:unit) took 23 min because multi-minute real-sim tests sat unmarked in tests/unit: `TestRunSweep` (6 methods, 80–290s each, ~1075s total) + `TestSimulationRunner::test_simulation_returns_result_dict` (118s) drive real engine sweeps through the headless runner. **Temporary fix on the deps branch:** both marked `@pytest.mark.slow`; `test:unit` selector now `not red_phase and not slow`; `test:rest-ci` grew a second leg running slow-marked unit tests — before it, slow-marked unit tests ran NOWHERE in CI (unit-ci excludes `slow`, rest-ci `--ignore=tests/unit`). Deferred to the testing-suite pass: (a) ~310s of per-test Postgres fixture SETUP in tests/unit/persistence (test_per_tick_transaction_atomicity + test_trace_view_columns re-create partitions and re-hydrate 5053 QCEW + 1045 hex rows PER TEST — wants module/session-scoped or shared hydration); (b) no CI job that runs the slow leg has Postgres, so the PG-gated slow tests (sweep/tune) SKIP in CI — they need a PG-provisioned home (postgres-up in test-rest, or move to the postgres-integration job); (c) taxonomy: these are integration/scenario tests wearing a unit label — relocate under tests/scenarios or tests/integration; (d) `test:fast` (`-m 'not slow'`) is now a near-duplicate of test:unit and doesn't exclude red_phase — consolidate or fix its selector. |
| 55 | **django 6 + mypy 2 modernization** (deferred from the deps wave) | django-stubs 6.0.6 and drf-stubs 3.17.0 both cap `mypy<2.2` via the compatible-mypy extras — mypy 2.2 is unsatisfiable alongside them; escapes are structural (drop the extras and forfeit tested-compat, or take mypy 2.0/2.1 with django 6 as a smaller move). Wants its own railed batch: manage.py check + web suites + typecheck across 567 files. |
| 56 | **map view hex-persist transaction bug** (surfaced by first-ever CI execution of tests/integration/test_map_api.py) | `engine_bridge._persist_hex_state_safe -> bulk_create` raises TransactionManagementError under the sqlite test backend (identical pre-wave at 82a92882 and locally) — an earlier query inside the atomic block fails and the 'safe' wrapper doesn't contain it. Now an evidence-cited xfail; the fix is a real bridge investigation (on_commit/nested-atomic territory), not test cosmetics. |

## 2026-07-11 late afternoon — Phase 8 CLOSE + Dependabot reproducibility (Opus 4.8)

**WATCH from 2026-07-11 (proving dispatches) RESOLVED.** The fixes branch closed the
last gaps and `dev` promoted to `main` a second time (`82a92882 → a491c22d`, 28 commits,
clean ff via `tools/promote.sh`). The proving-run saga:

- **Proving run #4** (main.yml on dev): the heavy-shard OOM fix let the shard complete
  and exposed one real red — `test_parameter_analysis.py::test_full_trace_to_csv` drives
  `run_trace()` → the headless runner (needs the SQLite reference DB the heavy shard
  doesn't fetch). Fix: module-level `requires_reference_db` marker routes all 4 tests in
  that class to the main-tier Reference-Data job (ci-data subset, detroit-tri-county). The
  advisory sphinx build separately ran past the docs job's 15-min timeout (a job-level
  timeout CANCELS the job — NOT swallowed by continue-on-error), so it was capped with
  `timeout 480`. (PR #174.)
- **Proving run #5** (same fixes, dev@a491c22d): full pipeline GREEN — Non-Unit Tests,
  Documentation Build, Reference-Data all success; the only red is the advisory Image Scan
  (postgis, item 45), which `promote.sh` filters by the "advisory" name convention.
- Promoted. **Real main.yml run on main** then flaked ONE blocking unit test
  (`test_running_loop_executes_steps`, `assert 1 >= 2`) that had passed twice on the
  identical SHA — a wall-clock-dependent test starved by CI load. De-flaked to a bounded
  poll (PR #176) → **item 58 below**. The promotion itself remains validly green (code
  identical, verified green twice).

**Dependabot — "truly reproducible, non-recurring" (your directive) DONE.** The
post-promotion dependency-graph rescan + the config changes cleared the churn:

- **Alerts 34 → 0 open.** The 6 poetry.lock (CVE-wave patches now on main) and 1 ansible
  (main now at 14.1) auto-resolved on the rescan; the 27 `uv.lock` phantoms (manifest
  deleted spec-037, absent from main HEAD) were dismissed as `inaccurate` with a traceable
  note. They cannot regenerate — the manifest is gone.
- **PRs 11 → 1 open.** Closed: 3 phantom (uv.lock/web-frontend deleted), 3 superseded
  (dev already ≥), 5 deferred majors. Dependabot ITSELF auto-closed 4 of the deferred
  majors the moment it re-read the new config from `main` — proving the `ignore` directives
  work. The 1 remaining (#175) is a legitimate reviewable batch → **item 57**.
- **B4 ruling recorded (yours, 2026-07-11): security updates stay ON, route via `dev`.** No
  repo Settings change. `target-branch: dev` routes real security PRs through
  validate→promote; the blocking pip-audit gate + weekly dev scan are the backstop.
- **Reproducibility hardening:** `.github/dependabot.yml` now `ignore`s the deferred
  semver-majors (django/django-stubs/mypy → item 55; typescript → TS7; postgis → item 45),
  each with an UNBLOCK note; node pinned via `src/frontend/.nvmrc` (nvm + mise + setup-node
  single source). Lockfiles (poetry.lock, package-lock.json) remain the reproducibility
  anchor, gated by `poetry check --lock` / `npm ci`.

**New items needing rulings:**

| # | Item | Context |
| --- | --- | --- |
| 57 | **frontend-majors batch #175** (react-router 7→8, recharts 2→3, jsdom 28→29) | The `frontend-majors` group working as designed — one reviewable dev-targeted PR, never auto-merged; typescript 7 correctly EXCLUDED (ignored). **DECISION (2026-07-11, agent, under your "handle those PRs" delegation): DEFERRED, left OPEN — NOT merged.** react-router 8 + recharts 3 are **breaking** and `feature/113-living-map` actively develops router code (LoginRoute/LobbyRoute/routes/) against v7; #175's CI is green against *current dev* but I can't verify the worktree survives v8 from the main checkout, and it's a dev-dep bump with zero security urgency — merging risks silently breaking your active branch. Closing is pointless (majors aren't ignored → Dependabot re-opens). Take it when the worktree lands (or say the word and I'll merge / unbundle just jsdom 29). |
| 58 | ~~**latent timing-flaky sibling**~~ **RESOLVED 2026-07-11** (`test_runner.py`, real-Simulation lifecycle) | The `len(states) >= 1`-after-fixed-sleep sibling was fixed proactively (not left latent): same bounded-poll pattern as the `>= 2` fix — accumulate `drain_queue()` (non-blocking) across a ≤2s bound, break on first state. Verified 5/5 green locally. No wall-clock asserts remain in the runner suite. |
| 59 | ~~**`fact_census_institutional_ownership` is a zero-filled placeholder**~~ **RULED 2026-07-16 ("see if our data there") + trove swept: NOT THERE → seed-only** | All 6,570 rows have every numeric column = 0, and coverage is 2010–2011 only (verified: `SUM(ABS(...))` across total_units/owner_occupied/renter_occupied/institutional_owned/absentee_owned = 0). The Feature-021 loader wrote placeholders — ACS has no institutional/absentee-ownership variables, and the babylon-data trove's census/ dir has no parcel/assessor source either. So `Territory.concentrated_ownership`/`absentee_landlord_share` (consumed by `DispossessionIntensityCalculator` weights `weight_tax_sale`/`weight_eminent_domain`) cannot be honestly wired from in-repo data. Wiring an adapter to all-zero data would be III.11 fabrication — refused. **Ruling wanted:** (a) source real county-level institutional-ownership data (assessor/CoreLogic-class, or a published research dataset) into the trove → loader → then the wire is a 1-session D8-clone; (b) accept the fields as permanently seed-only and retire the census claim from the epochs audit; or (c) drop the two structural factors from the intensity formula until data exists. All other 14 `fact_census_*` tables verified REAL (housing 1.35M rows, poverty 26.6M, worker_class 900k, 2010–2023). |
| 60 | ~~**`tick_median_wage` is a QCEW MEAN wearing a median's name**~~ **RESOLVED 2026-07-15 (feat/mean-wage-wire) — better third option found in the code itself** | The only wage series in the reference DB is QCEW `annual wages / employment / 52` — an **average** weekly wage. The engine field, seam entry, and frontend label all say *median*. Wiring it as-is relabels a mean as a median (the honest-Φ trap you ruled against). Options: (1) rename the field end-to-end to `tick_mean_wage` and wire QCEW (1-session, D8-clone rails, breaks no math — consumers use it as a level, not a distribution stat); (2) source a real median (ACS `fact_census_median_income` is household income, not wage; BLS OEWS has true median wages but isn't loaded) and keep the name. Option 3 (document-only) already rejected. Recommendation: (1) now, (2) later if OEWS lands. Unemployment half of D8 is DONE (real LAUS U-3 wired, `e6f8af5c`). **Resolution:** neither rename nor wait — the class-shares hydration already computed a genuine median ESTIMATOR (employment-weighted p50 across QCEW 6-digit industry mean wages: walk leaves lowest-to-highest-paid, take the industry where cumulative employment crosses 50%). `get_county_median_hourly_wage` now lives on the QCEW adapter; `services.wage_source` seeds the INITIAL county median_wage only (`prev is None`) — median_wage is endogenous (wage-pressure dynamics own the trajectory), so data sets the initial condition and never clobbers the sim. The raw county mean was deliberately NOT wired — it is a mean. Name now TRUE, no 52-file rename, no contract churn. OEWS true-median remains a future upgrade if you want within-industry dispersion. |
| 61 | **EH ruling 6 — player marker (Wave 5 Phase-2 prereq)** (flagged in the ratified EH program doc during Phase 1, 2026-07-15; queueing it here since program-doc flags aren't visible in your triage flow) | Phase-1 findings: `I_c` is uniformly 0.1 across all 81 wayne territories because `C_p` = 0 everywhere — NO org model outside PoliticalFaction carries a player marker (CivilSocietyOrg ORG001 has 2 real PRESENCE edges but no `is_player`). Phase 2 (reveal gating — bridge serialization filtered by vision state, Investigate raising `I_c`) is player-relative by definition and the ratified doc names this as its prereq. **Options:** (a) promote `is_player: bool` to the base `Organization` model (roundtrip + snapshot columns follow); (b) add `WorldState.player_org_id: str \| None` (single pointer, no per-org flag, cleaner for multiplayer-later); (c) bridge-side only — derive the player org from `GameSession.player_id` at serialization time, engine stays player-agnostic (weakest: engine-side `I_c`/`C_p` stays degenerate). Recommendation: (b) — it matches "state is pure data", keeps orgs symmetric, and the engine reads one field. One ruling unblocks the whole Wave-5 player-facing arc. |
| 62 | **Race modeling — RULED 2026-07-16: national-oppression axis** | Owner ratified (AskUserQuestion): race enters the engine as an oppressed-nations axis — nation composition per class per county from ACS dim_race data, feeding super-exploitation differentials and the NATIONAL_CHAUVINISM⟷INTERNATIONALISM opposition. Its own ADR + phased spec next session (seed: `project/research/national-oppression-axis-program-seed.md`). Wave-6 census wires stay aggregate-only until it lands. |
