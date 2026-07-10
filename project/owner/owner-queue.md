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
