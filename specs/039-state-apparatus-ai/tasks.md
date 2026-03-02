# Tasks: State Apparatus AI (Feature 039)

**Input**: Design documents from `/specs/039-state-apparatus-ai/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per project TDD mandate (CLAUDE.md: "TDD: Red-Green-Refactor cycle mandatory").

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and package scaffolding for state AI subsystem

- [ ] T001 Create source directory structure: `src/babylon/ooda/state_ai/` and `src/babylon/ooda/attention/` with `__init__.py` files per plan.md project structure
- [ ] T002 [P] Create test directory structure: `tests/unit/state_ai/`, `tests/contract/state_ai/`, and `tests/integration/` with `conftest.py` files including DomainFactory fixtures for state AI entities
- [ ] T003 [P] Add state AI test constants (Detroit 2010 defaults, faction thresholds, budget values, thread parameters) to `tests/constants.py` following existing TestConstants frozen dataclass pattern

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core enums, entity models, configuration, and protocols that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Phase

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 Write unit tests for StateFaction, StateActionType, ThreadPhase, SurveillanceMethod enums (membership, string values, exhaustiveness) in `tests/unit/state_ai/test_state_verbs.py`
- [ ] T005 [P] Write unit tests for VERB_CHILDREN hierarchy (all top-level verbs have children, all sub-verbs have exactly one parent, no orphans) in `tests/unit/state_ai/test_state_verbs.py`
- [ ] T006 [P] Write unit tests for FactionBalance model (weight normalization sum-to-1.0, computed dominant_faction, immutability, model_copy mutation, Detroit 2010 defaults) in `tests/unit/state_ai/test_faction_balance.py`
- [ ] T007 [P] Write unit tests for StateBudget model (revenue >= available, top-level-only allocation keys, no overdraft, zero-budget edge case) in `tests/unit/state_ai/test_state_verbs.py`
- [ ] T008 [P] Write unit tests for StateAction model (verb hierarchy validation rejects invalid parent-child, budget_cost >= 0, faction_alignment valid) in `tests/unit/state_ai/test_state_verbs.py`
- [ ] T009 [P] Write unit tests for LegalFramework model (scope validation, severity bounds, effects dict) in `tests/unit/state_ai/test_state_verbs.py`
- [ ] T010 [P] Write unit tests for AttentionThread model (target_type validation, phase enum, intel_completeness bounds, frozenset observed sets) in `tests/unit/state_ai/test_attention_threads.py`
- [ ] T011 [P] Write unit tests for SparrowAnalysis model (equivalence_classes partition observed nodes, singletons subset, confidence bounds) in `tests/unit/state_ai/test_sparrow.py`

### Implementation for Foundational Phase

- [ ] T012 Add StateFaction, StateActionType, ThreadPhase, SurveillanceMethod enums to `src/babylon/models/enums.py` with Sphinx-compatible docstrings per data-model.md definitions
- [ ] T013 Add TARGETS and OWNED_BY edge types to EdgeType enum in `src/babylon/models/enums.py` (R-003: threads as graph nodes with typed edges to targets and owning apparatus)
- [ ] T014 Implement VERB_CHILDREN constant (parent→frozenset[child] mapping) and `get_parent_verb()` helper in `src/babylon/models/entities/state_apparatus_ai.py`
- [ ] T015 [P] Implement FactionBalance frozen Pydantic model with weight normalization validator and computed `dominant_faction` property in `src/babylon/models/entities/state_apparatus_ai.py`
- [ ] T016 [P] Implement StateBudget frozen Pydantic model with revenue/allocation validators in `src/babylon/models/entities/state_apparatus_ai.py`
- [ ] T017 [P] Implement StateAction frozen Pydantic model with verb hierarchy validation (sub_verb must be child of verb per VERB_CHILDREN) in `src/babylon/models/entities/state_apparatus_ai.py`
- [ ] T018 [P] Implement LegalFramework frozen Pydantic model with scope and severity validation in `src/babylon/models/entities/state_apparatus_ai.py`
- [ ] T019 Implement AttentionThread frozen Pydantic model with target_type validation in `src/babylon/models/entities/attention_thread.py`
- [ ] T020 [P] Implement ObservationModel (surveillance method capabilities per apparatus) in `src/babylon/models/entities/attention_thread.py`
- [ ] T021 [P] Implement SparrowAnalysis frozen Pydantic model in `src/babylon/models/entities/attention_thread.py`
- [ ] T022 Add StateApparatusAIDefines sub-model (faction_verb_preferences, fascist thresholds, thread escalation thresholds, budget defaults, territory effect parameters, all configurable constants from spec) to `src/babylon/config/defines.py`
- [ ] T023 Extend StateApparatus entity with `factional_alignment: StateFaction` field in `src/babylon/models/entities/organization.py` (FR-C08)
- [ ] T024 Implement NPCDecisionStrategy protocol (select_action method signature) in `src/babylon/ooda/state_ai/protocols.py` (FR-D09)
- [ ] T025 Update model package exports: add new entities to `src/babylon/models/entities/__init__.py` and new enums to `src/babylon/models/__init__.py`

**Checkpoint**: All entity models pass validation tests. Enums are accessible. StateApparatusAIDefines loads defaults. Protocol is importable. Foundation ready for behavior implementation.

______________________________________________________________________

## Phase 3: User Story 1 — State Responds with Faction-Weighted Verbs (Priority: P1) MVP

**Goal**: Implement the state AI decision function that selects verbs based on factional objective function, budget constraints, and escalation logic. This is the minimum viable enemy.

**Independent Test**: Run a 52-tick simulation where player generates increasing Heat. Verify state verb selections shift from CO-OPT through REPRESS in a legible escalation sequence. Different FactionBalance weights produce different verb rankings.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [US1] Write contract tests for D-01 (factional objective scoring: different FactionBalance weights produce different action rankings) and D-02 (budget constraint: zero-budget yields zero-cost actions only) in `tests/contract/state_ai/test_decision_contract.py`
- [ ] T027 [P] [US1] Write contract tests for D-03 (escalation: monotonic Heat increase shifts verbs up the escalation ladder) and D-04 (de-escalation: Heat drop shifts verbs back to low-cost) in `tests/contract/state_ai/test_decision_contract.py`
- [ ] T028 [P] [US1] Write contract tests for D-05 (determinism: identical seed + state produces identical action sequences) and D-06 (one-action-per-tick default, configurable actions_per_tick) in `tests/contract/state_ai/test_decision_contract.py`
- [ ] T029 [P] [US1] Write unit tests for faction-specific objective functions (FC maximizes extraction/profit/stability, SS maximizes threat suppression, SP maximizes settler property values) in `tests/unit/state_ai/test_escalation.py`

### Implementation for User Story 1

- [ ] T030 [US1] Implement faction-specific objective sub-functions (finance_capital_objective, security_state_objective, settler_populist_objective) returning float scores per candidate action in `src/babylon/ooda/state_ai/decision.py`
- [ ] T031 [US1] Implement candidate action generation (enumerate feasible sub-verbs given budget and thread constraints) and factional objective scoring (weighted sum of faction scores) in `src/babylon/ooda/state_ai/decision.py`
- [ ] T032 [US1] Implement budget constraint enforcement (action.budget_cost <= budget.available, no overdraft, budget deduction on selection) in `src/babylon/ooda/state_ai/decision.py`
- [ ] T033 [US1] Implement escalation ladder ranking and verb-selection logic (prefer low-cost/low-visibility first, escalate when cheaper options fail or threat rises) in `src/babylon/ooda/state_ai/escalation.py`
- [ ] T034 [US1] Implement de-escalation logic (when Heat subsides, re-score shifts toward low-cost options; when CO-OPT succeeds, reduce REPRESS preference) in `src/babylon/ooda/state_ai/escalation.py`
- [ ] T035 [US1] Implement basic faction shift formula (Heat → Security-State weight increase, clamped to max_faction_shift_per_tick) in `src/babylon/formulas/state_ai.py`
- [ ] T036 [US1] Implement RuleBasedStateAI class satisfying NPCDecisionStrategy protocol (select_action: OBSERVE→ORIENT→DECIDE→ACT per-tick flow) in `src/babylon/ooda/state_ai/decision.py`
- [ ] T037 [US1] Integrate state AI decision into OODA system: extend `src/babylon/ooda/npc_stub.py` to delegate StateApparatus org_type to RuleBasedStateAI.select_action instead of existing _NPC_PRIORITIES lookup
- [ ] T038 [US1] Implement state action resolution dispatch in `src/babylon/engine/systems/ooda.py` — when StateAction is emitted, apply budget deduction and emit action events via EventBus

**Checkpoint**: State AI selects verbs based on faction weights. Budget is enforced. Escalation/de-escalation is legible. Deterministic given seed. US1 acceptance scenarios pass.

______________________________________________________________________

## Phase 4: User Story 2 — Attention Threads Track Player Organization (Priority: P2)

**Goal**: Implement the attention thread intelligence system: thread allocation, G_observed construction, Sparrow analysis, and observation gap mechanics. The state's ability to "see" the player.

**Independent Test**: Create an FBI attention thread targeting a star-topology org. Advance 12 ticks. Verify intel_completeness grows, observed_subgraph expands, Sparrow identifies hub as singleton. Cell-topology org shows at least 30% lower intel.

### Tests for User Story 2

- [ ] T039 [US2] Write contract tests for T-01 (intel growth over 8 ticks), T-02 (cell topology 30% resistance), and T-03 (observation ceiling cap per apparatus) in `tests/contract/state_ai/test_thread_contract.py`
- [ ] T040 [P] [US2] Write contract tests for T-04 (Sparrow singleton identification on star topology), T-05 (meta-OODA threat-based allocation), and T-06 (observation gap distortions per method) in `tests/contract/state_ai/test_thread_contract.py`

### Implementation for User Story 2

- [ ] T041 [US2] Implement G_observed construction: build separate DiGraph from thread's observed_node_ids/observed_edge_ids with method-specific distortions (edge type conflation, temporal flattening, cash invisibility, face-to-face blindness) in `src/babylon/ooda/attention/observation.py`
- [ ] T042 [US2] Implement observation ceiling enforcement: effective_ceiling = base_ceiling * (1 - compartmentalization_factor), intel_completeness hard-capped at ceiling in `src/babylon/ooda/attention/observation.py`
- [ ] T043 [US2] Implement Sparrow network analysis on G_observed: centrality computation (degree, betweenness, closeness, eigenvector via NetworkX), equivalence class computation via numerical signatures, singleton identification, and minimal cutset detection in `src/babylon/ooda/attention/sparrow.py`
- [ ] T044 [US2] Implement per-thread OODA cycle: OBSERVE (expand observed_subgraph based on surveillance_method), ORIENT (run Sparrow analysis), DECIDE (choose targeting strategy), ACT (execute intel action) in `src/babylon/ooda/attention/thread_ooda.py`
- [ ] T045 [US2] Implement thread allocation meta-OODA: score targets by (heat_level, community_CI, org_size, recent_heat_events), allocate greedily with stickiness bonus for long-tracked targets, deallocate lowest-priority on pool saturation in `src/babylon/ooda/attention/thread_manager.py`
- [ ] T046 [US2] Implement thread phase transitions (DORMANT→MONITORING→ACTIVE_INVESTIGATION→DISRUPTION) driven by intel_completeness thresholds from StateApparatusAIDefines; phase does NOT regress during active tracking in `src/babylon/ooda/attention/thread_manager.py`
- [ ] T047 [US2] Write unit tests for Sparrow analysis algorithms (centrality on known graph structures, equivalence classes on star/cell topologies, cutset detection) in `tests/unit/state_ai/test_sparrow.py`
- [ ] T048 [US2] Write unit tests for thread lifecycle (allocation, phase transitions, stickiness, deallocation, pool saturation handling) in `tests/unit/state_ai/test_attention_threads.py`

**Checkpoint**: Attention threads accumulate intelligence. Sparrow analysis identifies structural vulnerabilities on G_observed. Cell topology resists surveillance. Meta-OODA allocates threads by threat. US2 acceptance scenarios pass.

______________________________________________________________________

## Phase 5: User Story 3 — Factional Balance Shifts (Priority: P3)

**Goal**: Implement the full faction dynamics system: player action→faction shift, material condition triggers, fascist convergence detection, near-absorbing state mechanics. The state changes character based on player strategy.

**Independent Test**: Run two parallel 26-tick simulations with different player strategies. Verify faction balances diverge. Trigger fascist convergence conditions and verify qualitative behavioral shift.

### Tests for User Story 3

- [ ] T049 [US3] Write contract tests for F-01 (weight normalization), F-02 (Heat→SS shift with minimum effect floor), and F-03 (failed repression→SS decline) in `tests/contract/state_ai/test_faction_contract.py`
- [ ] T050 [P] [US3] Write contract tests for F-04 (fascist convergence three-pillar detection with confirmation window) and F-05 (near-absorbing state with asymmetric entry/exit thresholds) in `tests/contract/state_ai/test_faction_contract.py`

### Implementation for User Story 3

- [ ] T051 [US3] Implement player action→faction shift calculations (Heat→+SS, extraction disruption→+FC panic, legitimacy building→+FC CO-OPT pressure, surviving repression→-SS credibility, narrative victories→+SP reaction) in `src/babylon/ooda/state_ai/faction_dynamics.py`
- [ ] T052 [US3] Implement material condition→faction shift triggers (profit rate decline→+FC influence, imperial rent contraction→+SP panic, legitimacy crisis→+SS weight, successful CO-OPT→+FC) in `src/babylon/ooda/state_ai/faction_dynamics.py`
- [ ] T053 [US3] Implement faction balance re-normalization with per-tick delta clamping (max_faction_shift_per_tick=0.05) and stability metric computation from recent shift history in `src/babylon/ooda/state_ai/faction_dynamics.py`
- [ ] T054 [US3] Implement fascist convergence detection (SS>0.4 AND settler CI>0.6 ASSIMILATIONIST_FASCIST AND FC<0.25 for convergence_confirmation_ticks consecutive ticks) and near-absorbing exit thresholds (SS<0.25 AND settler CI<0.30) in `src/babylon/formulas/state_ai.py`
- [ ] T055 [US3] Implement fascist mode behavioral overrides: CO-OPT budget→REPRESS redirect, DEVELOP→displacement-oriented sub-verbs, WITHDRAW→SCORCHED_EARTH in contested territories, LEGISLATE→EMERGENCY_POWERS in `src/babylon/ooda/state_ai/faction_dynamics.py`
- [ ] T056 [US3] Integrate fascist convergence with EventBus: add FASCIST_CONVERGENCE to EventType enum in `src/babylon/engine/event_bus.py`, emit event when convergence first detected, consumed by BifurcationMonitor (Feature 033)

**Checkpoint**: Player strategies produce measurably different faction balances. Fascist convergence triggers qualitative behavioral shift. Near-absorbing state resists reversion. US3 acceptance scenarios pass.

______________________________________________________________________

## Phase 6: User Story 4 — DEVELOP and WITHDRAW Reshape Territory (Priority: P4)

**Goal**: Implement state territory verbs: INVEST raises property values, NEGLECT degrades infrastructure, DISPLACE removes population, STRATEGIC_WITHDRAWAL hollows territory, SCORCHED_EARTH destroys. Gentrification and disinvestment as first-class game mechanics.

**Independent Test**: Apply INVEST to territory over 8 ticks. Verify property_value_proxy rises and V_reproduction increases. Apply NEGLECT for 12 ticks and verify exponential infrastructure decay with quality floor.

### Tests for User Story 4

- [ ] T057 [US4] Write contract tests for BC-TE-001 (INVEST property value increase), BC-TE-002 (NEGLECT exponential decay with floor), and BC-TE-003 (DISPLACE population removal, TENANCY severance, CI decrease) in `tests/contract/state_ai/test_territory_contract.py`
- [ ] T058 [P] [US4] Write contract tests for BC-TE-004 (STRATEGIC_WITHDRAWAL state PRESENCE removal, infrastructure hollowing) and BC-TE-005 (SCORCHED_EARTH infrastructure destruction, visibility-based legitimacy cost) in `tests/contract/state_ai/test_territory_contract.py`

### Implementation for User Story 4

- [ ] T059 [US4] Implement INVEST action resolution: increment property_value_proxy by invest_property_delta per tick, increase V_reproduction for TENANCY-connected SocialClass nodes, increase rent_level, emit TERRITORY_INVESTED event in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T060 [US4] Implement NEGLECT action resolution: exponential infrastructure_quality decay (quality *= 1 - neglect_decay_rate), enforce neglect_quality_floor, degrade property_value_proxy and territory services proportionally, emit TERRITORY_NEGLECTED event in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T061 [US4] Implement DISPLACE action resolution: remove population (displace_population_fraction), sever TENANCY edges via graph.remove_edge(), decrease community_infrastructure_quality and collective_identity, relocate displaced blocks to adjacent affordable territories or DISPLACED state, emit TERRITORY_DISPLACED event in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T062 [US4] Implement STRATEGIC_WITHDRAWAL action resolution: remove all state apparatus PRESENCE edges (preserve non-state PRESENCE), accelerated infrastructure degradation, set state_investment to 0.0, increase V_reproduction, optionally recover budget fraction when asset_extraction=True in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T063 [US4] Implement SCORCHED_EARTH action resolution: set infrastructure_quality to neglect_quality_floor or below (immediate destruction), compute legitimacy_cost proportional to territory visibility (CORE=extreme, PERIPHERY=minimal), destroy community infrastructure, remove state PRESENCE edges, spike V_reproduction in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T064 [US4] Write unit tests for territory effect calculations (property_value_proxy increments, exponential decay math, population fraction removal, adjacency-based relocation) in `tests/unit/state_ai/test_territory_effects.py`
- [ ] T083 [US4] Implement NEGOTIATE resolution mechanic (FR-B11): when state selects WITHDRAW or CO_OPT, optionally enter negotiation phase evaluating concession cost vs continued repression cost; produce BRIBE/GRANT offers (CO_OPT path) or TACTICAL_RETREAT terms (WITHDRAW path); NEGOTIATE is not a standalone verb but a resolution modifier on existing verbs in `src/babylon/ooda/state_ai/decision.py`

**Checkpoint**: INVEST, NEGLECT, DISPLACE, STRATEGIC_WITHDRAWAL, SCORCHED_EARTH, and NEGOTIATE all produce measurable territory changes. Gentrification circuit (INVEST→DISPLACE) is functional. US4 acceptance scenarios pass.

______________________________________________________________________

## Phase 7: User Story 5 — Organization-Territory Spatial Dynamics (Priority: P5)

**Goal**: Implement PRESENCE edge mechanics, heat accumulation from operational profile, territorial recruitment requirement, consciousness geography, and eviction cascade. Spatial strategy becomes meaningful.

**Independent Test**: Place two orgs (HIGH_PROFILE and LOW_PROFILE) in same territory. Advance 8 ticks. Verify differential heat accumulation and recruitment eligibility based on PRESENCE.

### Tests for User Story 5

- [ ] T065 [US5] Write contract tests for BC-TE-006 (HIGH_PROFILE generates more heat than LOW_PROFILE, heat decays when PRESENCE removed, heat bounded [0,1]) in `tests/contract/state_ai/test_territory_contract.py`

### Implementation for User Story 5

- [ ] T066 [US5] Implement heat accumulation from PRESENCE edges: per-tick heat contribution proportional to operational_profile weight (high_profile_heat_rate > low_profile_heat_rate), heat decay without activity, heat bounded to [0,1] Intensity type in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T067 [US5] Implement territorial PRESENCE requirement for RECRUIT: organizations without PRESENCE in a territory cannot recruit population there, or recruitment effectiveness severely reduced (FR-E07) in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T068 [US5] Implement consciousness geography: collective_identity varies spatially per territory, EDUCATE actions produce local consciousness shifts before community-wide effects, territory-level CI informs state threat prioritization (FR-E04) in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T069 [US5] Implement eviction cascade: DISPLACE scatters organized communities, lowers local collective_identity, severs community infrastructure in specific territory, shifts territory demographic composition (FR-E06), extending DISPLACE resolution from T061 in `src/babylon/ooda/state_ai/territory_effects.py`
- [ ] T070 [US5] Write unit tests for heat mechanics (accumulation rates, decay curve, bounded output, threshold triggers) and recruitment PRESENCE check in `tests/unit/state_ai/test_territory_effects.py`

**Checkpoint**: Operational profile drives heat. Recruitment requires territorial presence. Consciousness varies spatially. Displacement has organizational consequences. US5 acceptance scenarios pass.

______________________________________________________________________

## Phase 8: User Story 6 — State CO-OPT Targets Consciousness and Leadership (Priority: P6)

**Goal**: Implement CO-OPT verb effects: PROPAGANDIZE reduces collective_identity (resisted by high consciousness), INCORPORATE removes KeyFigures, DIVIDE degrades solidarity edges, BRIBE creates transactional edges. Ideological warfare as gameplay.

**Independent Test**: Apply PROPAGANDIZE (WE_ARE_ALL_AMERICANS) to a community for 8 ticks. Verify collective_identity decreases. Verify high-CI territories resist more effectively than low-CI territories.

### Tests for User Story 6

- [ ] T071 [US6] Write contract test for BC-TE-007 (PROPAGANDIZE less effective in high-consciousness territory, spatially local effect, CI bounded [0,1]) in `tests/contract/state_ai/test_territory_contract.py`

### Implementation for User Story 6

- [ ] T072 [US6] Implement PROPAGANDIZE action resolution: apply narrative-specific CI decrease (WE_ARE_ALL_AMERICANS attacks collective_identity, THREAT_NARRATIVE raises settler CI), effectiveness reduced by consciousness_resistance_factor * target CI, spatially local per FR-E04 in `src/babylon/ooda/state_ai/co_opt_effects.py`
- [ ] T073 [US6] Implement INCORPORATE action resolution: acceptance probability inversely proportional to org Coherence and community collective_identity, if accepted remove KeyFigure from player org and create state-aligned node, requires prior SURVEIL intelligence in `src/babylon/ooda/state_ai/co_opt_effects.py`
- [ ] T074 [US6] Implement DIVIDE action resolution: target SOLIDARISTIC edges between organizations, degrade edge type SOLIDARISTIC→TRANSACTIONAL→ANTAGONISTIC per Constitution I.15 edge mode transition rules, requires prior SURVEIL intelligence, methods (RUMOR, SELECTIVE_LEAK, PROVOCATEUR, FUND_RIVAL, IDENTITY_WEDGE) in `src/babylon/ooda/state_ai/co_opt_effects.py`
- [ ] T075 [US6] Implement BRIBE action resolution: transfer material resources to target (GRANT, TAX_BREAK, WAGE_CONCESSION), create TRANSACTIONAL edge between state and target, shift consciousness toward ASSIMILATIONIST_LIBERAL tendency in `src/babylon/ooda/state_ai/co_opt_effects.py`
- [ ] T076 [US6] Write unit tests for CO-OPT effect calculations (CI decrease with resistance factor, acceptance probability formula, edge type degradation sequence, BRIBE edge creation) in `tests/unit/state_ai/test_territory_effects.py`

**Checkpoint**: PROPAGANDIZE, INCORPORATE, DIVIDE, and BRIBE all produce measurable effects. High-consciousness territories resist CO-OPT. Edge mode transitions follow Constitution I.15. US6 acceptance scenarios pass.

______________________________________________________________________

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, graph serialization, debug tools, and cross-story validation

- [ ] T077 Write 52-tick integration test: full escalation-deescalation-fascist convergence scenario with all subsystems active (decision, threads, faction dynamics, territory effects) in `tests/integration/test_state_ai_integration.py`
- [ ] T078 [P] Implement God Mode debug toggle (FR-D12): when enabled, expose all state internals (faction weights, budget allocation, thread targets, intel_completeness, AI decision scoring) to player via state attribute in `src/babylon/ooda/state_ai/decision.py`
- [ ] T079 [P] Extend WorldState.to_graph()/from_graph() to serialize and deserialize AttentionThread nodes with TARGETS and OWNED_BY edges in `src/babylon/models/world_state.py`
- [ ] T080 [P] Add LegalFramework persistence: LEGISLATE creates framework entities stored in context.persistent_data, REVOKE removes them, framework effects consumed by relevant verb resolution functions in `src/babylon/ooda/state_ai/decision.py`
- [ ] T081 Run mypy strict mode on all new modules (`src/babylon/ooda/state_ai/`, `src/babylon/ooda/attention/`, `src/babylon/models/entities/state_apparatus_ai.py`, `src/babylon/models/entities/attention_thread.py`) and fix any type violations
- [ ] T082 Validate quickstart.md test scenarios against implementation: verify code examples compile and described workflows produce expected results
- [ ] T084 [P] Implement player observability layer (FR-D11): surface state behavior through indirect signals — observable verb selections emitted as EventBus events with public-facing metadata (verb type, territory affected, visible intensity), territory-level effects visible via graph attributes (property_value_proxy, infrastructure_quality, heat_level). Player COUNTER_INTEL action reveals deeper internals (faction weights, thread targets) proportional to intelligence success in `src/babylon/ooda/state_ai/observability.py`

______________________________________________________________________

## Deferred Requirements

The following requirements are explicitly deferred from this feature with documented rationale:

- **FR-D10** (Per-org-type AI for Business, CivilSocietyOrg, PoliticalFaction): **Deferred** — Feature 039 focuses exclusively on StateApparatus AI. Non-state org-type AI decision functions (Business employ/lobby, CivilSocietyOrg tendency-based, PoliticalFaction strategy-based) are a separate feature scope that depends on this feature's NPCDecisionStrategy protocol (T024) being stable. Recommend: Feature 040 or later.
- **FR-E05** (D-P-D' territory infrastructure): **Deferred** — Schools (D-phase ideological transmission), workplaces (P-phase), and elder care (D'-phase) as territory-bound infrastructure entities require a lifecycle data model, initialization data (Detroit school/workplace locations), and integration with the consciousness system that exceeds this feature's scope. Territory-level aggregate effects (consciousness geography in T068, recruitment presence in T067) provide a functional approximation. Recommend: Feature 041 or later.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1): Can start immediately after Foundational
  - US2 (P2): Can start after Foundational (independent of US1)
  - US3 (P3): Depends on US1 (extends decision function with faction shift feedback loop)
  - US4 (P4): Depends on US1 (DEVELOP/WITHDRAW are state verbs resolved by decision system)
  - US5 (P5): Depends on US4 (spatial dynamics build on territory effects)
  - US6 (P6): Depends on US1 (CO-OPT verbs resolved by decision system); can parallel with US4
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 2 (Foundational)
    │
    ├──► US1 (Phase 3) ──► US3 (Phase 5)
    │        │
    │        ├──► US4 (Phase 6) ──► US5 (Phase 7)
    │        │
    │        └──► US6 (Phase 8) [parallel with US4]
    │
    └──► US2 (Phase 4) [parallel with US1]
```

### Within Each User Story

- Contract tests MUST be written and FAIL before implementation (TDD RED)
- Models before services
- Services before integration
- Core implementation before cross-cutting
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational test tasks (T004-T011) marked [P] can run in parallel
- All Foundational model implementations marked [P] can run in parallel (different entities in same/different files)
- US1 and US2 can start in parallel after Foundational phase
- US4 and US6 can run in parallel after US1
- All Polish tasks marked [P] can run in parallel

______________________________________________________________________

## Parallel Example: Foundational Phase

```bash
# Launch all model tests in parallel:
Task: "Write unit tests for FactionBalance model" (T006)
Task: "Write unit tests for StateBudget model" (T007)
Task: "Write unit tests for StateAction model" (T008)
Task: "Write unit tests for AttentionThread model" (T010)
Task: "Write unit tests for SparrowAnalysis model" (T011)

# Launch all model implementations in parallel (after tests):
Task: "Implement FactionBalance model" (T015)
Task: "Implement StateBudget model" (T016)
Task: "Implement StateAction model" (T017)
Task: "Implement LegalFramework model" (T018)
Task: "Implement ObservationModel" (T020)
Task: "Implement SparrowAnalysis model" (T021)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 acceptance scenarios independently
5. The state AI selects verbs, respects budget, escalates/de-escalates — minimum viable enemy is functional

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → Test independently → MVP enemy AI functional
3. Add US2 → Test independently → Intelligence-driven targeting
4. Add US3 → Test independently → Strategic depth (faction dynamics)
5. Add US4 → Test independently → Gentrification as weapon
6. Add US5 → Test independently → Spatial strategy matters
7. Add US6 → Test independently → Ideological warfare
8. Each story adds value without breaking previous stories

### Parallel Development Strategy

With two agents/threads:

1. Complete Setup + Foundational together
2. Once Foundational is done:
   - Agent A: US1 (decision function) → US3 (faction dynamics) → US4 (territory) → US5 (spatial)
   - Agent B: US2 (attention threads) → US6 (CO-OPT effects)
3. Polish phase after all stories integrate

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD RED phase)
- Commit after each task or logical group (per CLAUDE.md: commit early, commit often)
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All configurable parameters go in StateApparatusAIDefines — no magic constants (Constitution III.1)
- All models are frozen Pydantic — mutation ONLY via model_copy(update={})
- Observation gap (G_observed != G_actual) is fundamental — the state never sees the real graph
