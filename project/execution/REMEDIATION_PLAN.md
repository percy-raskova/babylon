<!-- Committed 2026-07-08 as the ratified execution record of the remediation program.
     Authority chain: project/09-program-full-game.md -> project/POST_ASSESSMENT.md ->
     project/HOLISTIC_REVIEW-2026-07-07.md -> THIS PLAN. Ratified by Percy 2026-07-07
     (plan-mode approval + 4 AskUserQuestion rulings recorded in Context). -->

# Babylon Remediation Program — "Loud Machine"

## Context

Two reviews (`project/POST_ASSESSMENT.md` + `project/HOLISTIC_REVIEW-2026-07-07.md`, a 15-agent
whole-repo sweep) established: the web product is unplayable (4 P0s), the engine has silently
dead/crashing layers (2 no-op systems, dead spec-070 collapse layer, unseeded RNG violating
Constitution III.7, `from_graph` as a crash minefield), the unit suite is RED at HEAD (0027/0028
migration self-conflict), dormant economics stacks run on hardcoded fallbacks, and every guardrail
that would have caught this is disarmed. Planning exploration added a **6th P0: ALL player verbs are
engine-side no-ops** — no dispatch layer exists; the bridge fakes per-action deltas by pre/post
diffing (`web/game/engine_bridge.py:1990-2018`).

Percy's mandate: (1) fix everything identified; (2) build loud-failure checks & balances so the
system tells us when things break; (3) implement the genuinely-unimplemented spec tail.

**Owner rulings (AskUserQuestion, 2026-07-07):** wire dormant Vol-I/II/III + tensor_hierarchy LIVE
(own phase, R-PROOF proofs each); FULL national perf effort (new spec → profile → optimize → pass
104 gate → run 105 capstone); revive needed frontend then DELETE dead code; baselines regenerate
freely, always with proof.md.

**Standing rules every branch:** feature branch → `dev` (never direct), conventional commits via
`mise run commit`, TDD red→green→refactor, merge-ready = `mise run check` green (ruff+format+mypy
strict+test:unit), `rg` not grep, no `git -C`. Baseline-affecting branches ship `proof.md` in the
same PR.

---

## Key design decisions

### A. Verb resolution (6th P0) — dispatch lives in OODASystem @14

The bridge already injects player actions into `persistent_context["player_actions"]`
(`engine_bridge.py:1929-1951`, `VERB_TO_ACTION_TYPE` at `:96-103`). The seam is
`OODASystem._resolve_for_organization` (`src/babylon/engine/systems/ooda.py:210-221`) which
currently wraps actions in blind `ActionResult(success=True)`. Replace with a
`VERB_RESOLVERS: dict[ActionType, Resolver]` registry in `src/babylon/engine/actions/__init__.py`;
missing resolver → `success=False, failure_reason=...` (loud, never silent success).

- 9 resolvers, uniform signature `resolve_<verb>(action, org_attrs, graph, services) -> ActionResult`,
  composing the existing zero-caller `babylon/ooda/action_effects.py` machinery
  (`resolve_action`/`compute_consciousness_delta`; fascist-verb graph mutation is the precedent).
  Only `mobilize.py` has a body today (adapt it); educate/attack/campaign are new files; the other
  5 are stub rewrites. `move` needs new `ActionType.MOVE`; investigate→MAP_NETWORK,
  negotiate→PROPOSE_ALLIANCE (both exist). Delete `UNSUPPORTED_VERBS` (`engine_bridge.py:105-107`).
- Effects channel back via `context.persistent_data["turn_resolution"]` (step() syncs it,
  `simulation_engine.py:713-726`); `resolve_tick` reads REAL per-action results instead of pre/post
  diffing; preview endpoints re-point at the resolvers' pure helpers so preview == resolution.
- **Graph-write contract:** every attr a resolver writes must be a model field OR in the matching
  `world_state.py:54-101` exclusion frozenset in the same commit (this is why Design B lands first).
- **Baseline-neutral by construction:** NPC actions keep the current path (routing NPCs through
  resolvers is a defines-gated follow-up with its own proof); player actions never occur in headless
  runs — assert baseline byte-identity in the PR.
- Canary: rewrite `tests/test_verb_simplex_canary.py` → `tests/contract/verbs/` with direct imports
  (missing resolver = collection FAILURE, not skip), 9 verbs × {registered, effect-class,
  from_graph-survives}.

### B. from_graph safety (crash minefield)

All in `src/babylon/models/world_state.py` + writers:
- Add `sovereigns: dict[str, Sovereign]` field; to_graph emission loop; from_graph `sovereign`
  branch injecting `id=node_id`, stripping computed `metabolic_impact`. **No persistence migration
  needed** (node_state.node_type VARCHAR(16) fits; payloads JSONB).
- Break the circular import: `sovereign.py:30`'s module-level `formulas.balkanization` import moves
  inside the `metabolic_impact` property (also un-breaks `mise run test:doctest` repo-wide).
- DecompositionSystem writer gets `id`/`name` (`decomposition.py:240-251`); from_graph else-branch
  gets defensive `setdefault("id", node_id)` + warning-on-missing-name (fail-soft + loud log).
- `threat_score` → `SOCIAL_CLASS_COMPUTED_FIELDS`; `institution_relations` → serialize via
  `G.graph` metadata + reconstruct; event replay (`_validate_event`) falls back to bare
  `SimulationEvent` on tagged-union miss (fixes the 60/79 crash).
- Edge-merge: to_graph pre-scans same-(source,target) pairs with differing edge_type and RAISES
  (fail-loud) + one-shot audit over live scenarios; `multigraph=True` re-key is a spec'd follow-up
  only if the audit finds legitimate collisions.

### C. The Loud Machine — 13 gates

| # | Gate | Runs at |
|---|---|---|
| C.1 | System-on-roundtrip: every system from `system_registry.all_systems()` runs on a `to_graph`-shaped wayne graph, then `from_graph` must not raise. Fixture rule: property fixtures come from to_graph, never hand-seeded `_node_type` strings (that masking is what hid the case bug) | pytest unit leg, every PR |
| C.2 | Determinism A/B: (a) in-process 10-tick two-run event-hash equality every PR; (b) full headless A/B nightly (`tools/determinism_check.py` + extended-analysis job) | PR + nightly |
| C.3 | Migration idempotency: fresh PG, apply all migrations TWICE, no error; assert no duplicate numeric prefixes (renumber one of the two 0031s → 0032) | pytest postgres leg |
| C.4 | CI Postgres leg: `services: postgres:16` + `POSTGRES_HOST` in ci.yml so `tests/integration/web/` testcontainers suites actually run (wayne_county so `_canonical_payload` sees real events) | ci.yml |
| C.5 | Playwright CI job: PG service → migrate → `seed_initial_game --scenario wayne_county` → export `SPEC061_TEST_SESSION_ID` → Django + Vite → run suite incl. NEW real submit→resolve→results spec, real-map-features assertion, games-list assertion (today's verb spec is render-only; map specs self-stub) | ci.yml |
| C.6 | Silent-degradation policy: `@degrades` decorator replaces the 17 `except Exception→empty-200` bridge blocks — logger.error + per-endpoint counter in `/health/detail` + `"status":"degraded"` envelope. Engine hydration fallbacks (`hydration/reference.py:374,466,541`): FAIL-LOUD in `--strict` runs (canonical runs never simulate on fabricated constants), warn+manifest-counter otherwise | runtime |
| C.7 | Stub-bridge visibility: envelope `"bridge": "engine"\|"stub"` + `X-Babylon-Bridge` header + amber frontend badge + production refuses stub fallback | runtime |
| C.8 | Wiring audit: runner startup logs wired-vs-None table for all TickDynamics services; NoDataSentinel drops logged with reason + counted in manifest (`tick/system/__init__.py:386-390` currently drops silently — why dead gamma went unnoticed) | runner log + manifest |
| C.9 | Test-infra re-arm: `strict_markers = true` ini (addopts flag is a verified no-op on pytest 9); register `contract`, apply `ai` via conftest (179 unmarked tests); add pytest-timeout; `-m "not red_phase"` parity in mise; red_phase triage (30 zombies); `HYPOTHESIS_PROFILE=slow` nightly; delete dead ui-tests CI job; canary fail-not-skip | pyproject/CI/mise |
| C.10 | deptry in CI (38 issues today; allowlist dynamic imports) | ci.yml + qa:deps |
| C.11 | Doc-reference linter `tools/check_doc_refs.py`: path refs in CLAUDE.md/ai must exist | pre-commit + CI |
| C.12 | Budget gates: unit tests for `tick_budget_check.py` (currently untested gate), CI-light wayne 3-tick budget smoke, documented `qa:nightly` for full storage/tick budgets (need the local reference DB) | PR-light + nightly local |
| C.13 | 'resolving' watchdog: `POST /games/{id}/recover/` + stale-status sweeper command (today a worker death wedges sessions forever, `api.py:1014-1034`) | runtime |

---

## Execution plan — phases → branches

### Phase 0 — Stop the bleeding (unit suite green, truth committed)
| Branch | Size | Contents |
|---|---|---|
| 0.1 `fix/game-session-schema-parity` | S | Commit working-tree models.py change + delete `postgres_schema.py:49` snapshot_json + fix `web/game/tests/conftest.py:26` stale DDL + remove stub re-ADD (`apps.py:166-170`). Red test already exists (test_schema_parity fails at HEAD) |
| 0.2 `fix/migration-0027-idempotent` | S | `0027:39` → bare `ON CONFLICT DO NOTHING` (composite key can't be named — session_id doesn't exist yet on fresh DBs); renumber dup 0031→0032; RED-first C.3 idempotency test. Un-reds the 10 PG-path unit failures |
| 0.3 `chore/test-infra-rearm` | M | C.9 items (canary conversion deferred to 2.4) |
| 0.4 `docs/commit-truth-and-push` | S | Commit POST_ASSESSMENT + HOLISTIC_REVIEW + plan; minimal state.yaml corrections; uncheck 105-T14; **push dev to origin** (183 commits on one disk) |

### Phase 1 — Playable web core loop
| Branch | Size | Contents |
|---|---|---|
| 1.1 `fix/tick-resolve-datetime` | S | `default=_json_default` at `_legacy.py:203` AND latent `:256-262`; **exclude event `timestamp` from canonical comparison** (both `_canonical_payload` + `_canonical_payload_for_tick` — retry idempotency); defense-in-depth `model_dump(mode="json")` at `engine_bridge.py:1982`. RED: datetime-event unit test + wayne resolve integration test |
| 1.2 `fix/seed-scenario-loud` | S | Unknown scenario → CommandError (today `michigan`/`us_nationwide` silently fall through to `us`, `engine_bridge.py:3040-3067`) |
| 1.3 `feat/map-hex-projection` | M | `_persist_hex_state_safe` sibling to `_persist_tick_events_safe`: upsert `hex_latest` from `snapshot["territories"]` (which carry h3_index/heat/pop via `_serialize_territory:3329-3360`; field-map precedent `seed_hex_data.py:52-68`) in `resolve_tick` AND at `create_game` tick-0. No schema change. RED: map features>0 after create_game |
| 1.4 `feat/frontend-live-verbs` | M | Revive dead pipeline: `gameStore.fetchVerbTargets` (`gameStore.ts:205-227`) + `lib/verbs/` registry into VerbPage; params nesting + label→enum translation; drop fixture import (`lib/verb-config.ts:17`); type `verbTargets`; fix the 3 deterministic Vitest reds (incl. spec-092 severity classifier) |
| 1.5 `test/e2e-real-loop` | M | C.4 + C.5 + NEW submit→resolve→results spec + real-map + games-list assertions. Land BEFORE 2.4 so verb engine work has a live harness |

### Phase 2 — Engine honesty + verb dispatch
| Branch | Size | Contents |
|---|---|---|
| 2.1 `fix/from-graph-safety` | M | All of Design B; lands C.1 gate RED→GREEN; un-breaks doctest gate |
| 2.2 `fix/territory-case-noops` | M | `reserve_army.py:59` + `dispossession_events.py:61` → `"territory"`; their non-model attr writes → exclusion sets or model fields (decide per attr); fix masking fixtures to to_graph shape. Baseline-affecting — regen deferred to 2.R |
| 2.3 `fix/engine-determinism` | S | `_resolve_rng` pattern into StruggleSystem (`struggle.py:312`); `seed=tick` at `topology_monitor.py:481` (param exists); deterministic tick-derived timestamps (`event_bus.py:47`, `interceptor.py:92`, `models/events/_legacy.py:99`); EventBus handler isolation (`event_bus.py:212-220`). Lands C.2(a). Baseline-affecting |
| 2.R `proof/baseline-regen-2026-07` | M | ✅ **CLOSED 2026-07-09** (delivered as the spec-109 A7 closure — proof: `specs/109-data-spine/proof-A7.md`): fresh 520-tick canonical COMPLETED twice (first completions post-`cc4a5303`; sessions `a8cbf1ab`/`970951e3`), `michigan-e2e.json` regenerated + diffed vs old (gated fields byte-identical by frozen-hex design; +9 year-boundary events = the real movement), A/B determinism 0-row two-directional EXCEPT across all 4 dynamic tables. *(Original scope: ONE regen covering 2.2+2.3+gamma wiring, closing the cc4a5303 R-PROOF violation.)* |
| 2.4 `feat/verb-dispatch-engine` | L | All of Design A. Baseline-neutral (assert byte-identity for headless). e2e verb spec from 1.5 goes green end-to-end |
| 2.5 `fix/web-session-hygiene` | S | C.13 watchdog + session-scope the global metadata (`get_metadata("game_defines_json")` at `engine_bridge.py:1913` is cross-session-contaminating) |

### Phase 3 — Loud machine completion
| Branch | Size | Contents |
|---|---|---|
| 3.1 `feat/degradation-envelope` | M/L | C.6 sweep + counters + /health/detail + hydration strict policy + C.7 stub visibility + frontend badge |
| 3.2 `ci/nightly-and-audits` | M | C.2(b) nightly A/B, C.10 deptry, C.11 doc-ref linter, C.12 budget tests + CI-light smoke + qa:nightly, Hypothesis slow nightly |

### Phase 4 — 059 monolith decompositions (falsely-checked debt; AFTER gates, BEFORE feature mass)
| Branch | Size | Contents |
|---|---|---|
| 4.1 `refactor/postgres-runtime-split` | L | `_legacy.py` (2,320) → session/tick/canonical/events modules; also un-monkey-patch `_spec_062.py` methods |
| 4.2 `refactor/engine-simulation-split` | M | `simulation/_legacy.py` (1,054) + fix false "persistent ServiceContainer" docstring |
| 4.3 `refactor/circulation-edge-transition` | L | `circulation/types/_legacy.py` (1,354), `edge_transition/_legacy.py` (877, 356-line `_build_transitions`); scenarios `_legacy` deletion; events domain-split. Check 059 boxes only as each lands |

### Phase 5 — Wire the dormant sim (owner ruling; R-PROOF each)
| Branch | Size | Contents |
|---|---|---|
| 5.1 `feat/gamma-atus-adapter` | M | Adapter over `fact_atus_reproductive_labor` (data already loaded, zero readers) → gamma_III leaves hardcoded 0.33 for covered years; C.8 manifest proves fallbacks→~0; regen + proof.md |
| 5.2 `feat/vol2-vol3-service-wiring` | L | Wire remaining ~13 TickDynamics service slots (credit/circulation/distribution/interest/transitions) via runner ServiceContainer; defines-gated; proof window per activation batch |
| 5.3 `feat/tensor-hierarchy-resolution` | M/L | Default wire-live per ruling; if profiling proves county_exposure supersedes it, present evidence to Percy BEFORE any retirement |
| 5.4 `fix/storage-contradiction` | M | Adjudicate spec-089 delta persistence vs observed 1,295 MB/tick full-hex writes; `qa:storage-budget` is the acceptance — **DONE 2026-07-08 (`fix/storage-contradiction-r2`): NOT a delta regression (metric artifact + per-SESSION partition accumulation, verdict in HOLISTIC_REVIEW §871 ADJUDICATED note); fixed the real spec-101 tick-0 commit-marker collision (`write_commit_marker=False`) + loud Gate A/B in runner + two-sided storage-budget floor; `qa:storage-budget` GREEN** |

### Phase 6 — Spec tails → national capstone (perf LAST)
| Branch | Size | Contents |
|---|---|---|
| 6.1 `docs/spec-checkbox-truth-sweep` | S | 030/069/058 + 001-040 flips WITH verification; one commit per range, `[record-reconciliation]` trailer |
| 6.2 `feat/spec-063-tail` | M | T042 wire BorderCommuteSynthesisLoader into initialize_session; T043 PairedCrossBorderEmissionEvaluator + ConservationAuditor registration; 5 missing integration tests |
| 6.3 `feat/spec-043-land-tail` | M | 4 remaining transitions (inheritance/eminent-domain/speculation/gentrification); ValueTensor4x3 intersection; retire static `equity_factor` (`wealth_proxy.py`, `economy_class.py`) |
| 6.4 `feat/faction-dynamics-green` | M | Turn the 20 red_phase faction tests green (spec-039 tail); attention-thread verification; spec-013 small tail |
| 6.5 `docs/supersessions` | S | Banners: 040-michigan, 004/006/007, 051/052; relocate babylon-v2 loose proposals; fix misnamed 045 filename |
| 6.6 `spec/106-national-perf` | XL | Author the never-written perf spec; profile national FIRST (research blames O(N²)-class ContradictionField/FieldDerivative, not hydration; also ConsciousnessSystem O(N×E) at `ideology.py:149,173`); optimize; ratify a NATIONAL budget.json (current is a Michigan proxy); pass 104 gate; run 105 canonical (≥20-tick floor, 200 target) + national baseline + proof.md |

### Phase 7 — Record repair
Single branch `docs/record-repair` (M): project/ status banners + README authority chain
(09 → POST_ASSESSMENT → HOLISTIC_REVIEW → this plan); regenerate (not patch) `ai/state.yaml`
from repo truth, archive the Dec-2025 fossil fold; rewrite topology-system/graph-abstraction yamls
(rustworkx reality) + architecture.yaml ChromaDB claim; backfill anti-patterns (fixture-mirror
tests, silent-degradation handlers); rewrite parent `game/CLAUDE.md` (phantom codebase) + rag
README; fix babylon/CLAUDE.md counts (formulas 64/19, registry 21, models re-exports,
`formulas.__all__` +6).

---

## Verification

- Per branch: `mise run check` (ruff+format+mypy strict+test:unit) + branch-specific tests named above.
- Phase 1 exit: seed wayne_county → browser/e2e: create → see map features → submit educate (200) →
  End Turn → tick advances → results show real verb-caused deltas → event log populated. The new CI
  jobs (Postgres leg + Playwright) green.
- Phase 2 exit: C.1 + C.2(a) green; `mise run test:doctest` collects; determinism A/B twice-identical;
  2.R proof.md committed with regenerated baseline.
- Phase 5 exit: C.8 manifest shows gamma fallback count ~0 for covered years; each wiring batch has
  proof.md; storage adjudication documented with qa:storage-budget green. (storage clause MET
  2026-07-08 — 5.4 landed `qa:storage-budget` GREEN + the HOLISTIC_REVIEW §871 adjudication note.)
- Phase 6 exit: 104 gate passes on NATIONAL measurements; 105 canonical run completes ≥20 ticks with
  liveness gates; national baseline bundle committed.

## Top risks

- Timestamp exclusion changes idempotency semantics for existing sessions → covered by un-skipped
  atomicity tests + retry test (1.1).
- Verb resolvers writing non-model attrs → per-resolver roundtrip tests + C.1 (why B precedes A).
- 2.2/2.3 shift sim outputs → single coordinated 2.R regen + proof; A/B gate proves the new world stable.
- Edge-merge loud failure fires on legitimate domain data → pre-merge collision audit; escalate to
  multigraph spec instead of raising blind.
- 059 refactors regress persistence → determinism A/B + migration idempotency + e2e as the harness
  (why Phase 4 sits after Phase 3).
- National effort stalls on the wrong target → profile before optimizing (spec-106 phase 1).

---

## Appendix — explorer-verified mechanics (reference for execution)

### Web/map/e2e (explorer 1)
- #6 second latent site `_legacy.py:256-262`; `_json_default` at `:45-53`; `_persist_events` already
  safe. Nothing reads event timestamps downstream (frontend wire types have no per-event timestamp).
- #7: `HexState` (table `hex_latest`) written ONLY by fixture `seed_hex_data.py`; read at
  `engine_bridge.py:883`; features built via `h3.cell_to_boundary` (`:889`). `hex_spatial_map`/
  `dynamic_hex_state` are runner-5433-only.
- `seed_initial_game` refuses stub bridge (good); prints session id for `SPEC061_TEST_SESSION_ID`.
- Playwright boots ONLY Vite; Django must be started by the CI job. `end-turn-flow.spec.ts` would
  fail on #6 today; `verb-submit.spec.ts` is render-only.
- `tests/integration/web/` testcontainers suites skip in CI (no POSTGRES_HOST/no PG service).
- Stub bridge: no client-visible marker today (`_envelope` at `api.py:108-120`).

### Engine seams (explorer 2)
- BabylonGraph is `multigraph=False`; payloads keyed `(source,target)` (`graph.py:79,83`);
  "dual edge-type keys" = edge_type+_edge_type within ONE payload. add_edge merges (`:240-243`).
- from_graph dispatch `world_state.py:484-505`; Sovereign model exists (`sovereign.py:35-114`);
  WorldState lacks the field; to_graph never emits sovereigns.
- CollapseTransition payloads (`collapse_transition.py:149-159,220-230`) lack `id`;
  Decomposition payloads (`decomposition.py:240-251`) lack `id`+`name`.
- `check_resilience` already takes `seed` (`topology_monitor.py:186`); caller omits it (`:481`).
- Live action path: bridge → `persistent_context["player_actions"]` → OODASystem; `TurnResolution`
  currently built and DISCARDED (`ooda.py:147-153`); `persistent_data` syncs back to bridge
  (`simulation_engine.py:713-726`). `action_effects.py` dispatch complete but zero callers.
- `engine/actions/`: 6 orphaned modules; only mobilize.py has a body (written against the nx-compat
  surface OODA provides via `_compat_graph`, `ooda.py:69`).
- ooda/ package is the live implementation library (state_ai wired via npc_stub) — not a rival.

### Spec tails (explorer 3)
- Pure checkbox lag: 030, 069, 058, most 0/N specs in 001-040.
- 063 real gaps: T042 (synthesis loader never instantiated at session init — only the report field
  exists, `postgres_initialization.py:107`), T043 (PairedCrossBorderEmissionEvaluator doesn't exist),
  5 test files missing.
- 059 falsely-CHECKED: postgres_runtime split T016-T023 [X] but never done; same for
  simulation/ (T026-T030), circulation/types (T071), edge_transition (T072); scenarios T068 +
  events T039 honestly unchecked.
- 043: HexTenureComposition + 3 transitions + ground-rent circuit LIVE; missing = 4 transitions,
  tensor intersection, equity_factor retirement.
- 104/105: michigan 5-tick = 2,040ms median/tick; national tick-1 never committed (34+min, 10GB);
  `105/research.md:103-104` blames O(N²)-or-worse contradiction field; budget.json ceilings top:
  ContradictionField 1800ms, FieldDerivative 1300ms, Consciousness 1100ms.
- Verbs: `VERB_TO_ACTION_TYPE` maps 6 (educate→EDUCATE, reproduce→RECRUIT,
  attack→ATTACK_INFRASTRUCTURE, mobilize→PROTEST, campaign→PROPAGANDIZE, aid→PROVIDE_SERVICE);
  `UNSUPPORTED_VERBS` = investigate/move/negotiate; `process_layer3` already applies
  heat/edge/infrastructure deltas from ActionResults each tick (`layer3.py:22-54`).
