# Tasks: Organization Base Model

**Input**: Design documents from `/specs/031-organization-base-model/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: TDD approach — Red-Green-Refactor. Test tasks write failing tests first; implementation tasks make them pass.

**Organization**: Tasks grouped by user story (P1-P7) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Paths relative to repository root (`src/babylon/`, `tests/`)

______________________________________________________________________

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package directories and scaffolding for the organization module.

- [ ] T001 Create src/babylon/organizations/ package with __init__.py and tests/unit/organizations/ directory with conftest.py stub

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Enums, types, defines, and test constants that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Write TDD tests for 6 new StrEnum classes (OrgType, ClassCharacter, TopologyType, LegalStanding, JurisdictionLevel, ServiceType) and 5 new EdgeType values (MEMBERSHIP, RECRUITMENT, EMPLOYMENT, COMMAND, PRESENCE) in tests/unit/organizations/test_enums.py — verify enum membership, string values, StrEnum behavior, and no collision with existing EdgeType values. RED phase: tests must fail.
- [ ] T003 Extend src/babylon/models/enums.py with 6 new StrEnum classes and 5 new EdgeType values per data-model.md. ClassCharacter has 6 values: BOURGEOIS, PETTY_BOURGEOIS, LABOR_ARISTOCRATIC, PROLETARIAN, LUMPEN, CONTESTED. TopologyType is a classification output enum (STAR, HIERARCHY, MESH, CELL) — not stored on Organization. GREEN phase: make T002 tests pass.
- [ ] T004 [P] Create src/babylon/organizations/types.py with three frozen Pydantic models: ConsciousnessDelta (collective_identity_delta, tendency_pressure, tendency_magnitude, source_org_id), CompositionResult (distribution dict, total_members, axis), and TopologyClassification (topology_type, articulation_points list, component_count, is_connected) per data-model.md computed types section.
- [ ] T005 [P] Extend src/babylon/config/defines.py with OrganizationDefines(BaseModel) containing 12 parameters per data-model.md OrganizationDefines table (elder_capacity_factor=0.2, tendency_modifier_revolutionary=0.15, tendency_modifier_liberal=-0.05, tendency_modifier_fascist=0.10, observation_ceiling_local_pd=0.2, observation_ceiling_fusion=0.5, observation_ceiling_fbi=0.4, cohesion_loss_per_key_figure=0.2, min_cohesion_threshold=0.05, credibility_default_faction=0.5, credibility_sovereign=0.8, credibility_chartered=0.6). Register as `organization: OrganizationDefines = Field(default_factory=OrganizationDefines)` on GameDefines. Add to docstring.
- [ ] T006 [P] Extend src/babylon/data/defines.yaml with `organization:` section containing all 12 OrganizationDefines parameters with their default values, following the existing YAML structure pattern.
- [ ] T007 [P] Extend tests/constants.py OrganizationDefaults dataclass with test defaults for all Organization base fields (cohesion, cadre_level, budget, heat, etc.), subtype-specific fields (violence_capacity, surveillance_capacity, employment_count, surplus_extraction_rate, legitimacy, etc.), IntelMethodology presets, and consciousness formula expected values. Follow the existing frozen dataclass pattern with source comments.

**Checkpoint**: Foundation ready — enums, types, defines, and test constants all in place.

______________________________________________________________________

## Phase 3: User Story 1 — Instantiate All Organization Types (Priority: P1)

**Goal**: All four organization subtypes instantiable with frozen Pydantic models, discriminated union dispatch, graph round-trip via WorldState.

**Independent Test**: Create one instance of each subtype with Detroit-specific parameters; verify properties, immutability, serialization, and graph round-trip.

### TDD Tests (RED Phase)

- [ ] T008 [P] [US1] Write TDD tests for Organization base model in tests/unit/organizations/test_organization_model.py — test creation with defaults, creation with all fields, Probability/Currency constraint enforcement (reject out-of-bounds), frozen immutability (mutation raises ValidationError), model_copy mutation produces new instance, JSON round-trip fidelity (model_dump_json/model_validate_json), headquarters_id must be in territory_ids validation, institutional_persistence must be None when is_institution=False. Follow patterns from tests/unit/models/components/test_organization.py.
- [ ] T009 [P] [US1] Write TDD tests for 4 subtypes and discriminated union in tests/unit/organizations/test_subtypes.py — test StateApparatus creation (jurisdiction, violence/surveillance capacity, IntelMethodology, legal_standing defaults to SOVEREIGN warning), Business creation (sector, employment_count non-negative, surplus_extraction_rate, revenue), PoliticalFaction creation (ideology, is_player, relationship_to_player), CivilSocietyOrg creation (service_type, legitimacy), discriminated union dispatch (correct subtype from org_type literal), all four Detroit scenario instances from quickstart.md Scenarios 1-4.
- [ ] T010 [P] [US1] Write TDD tests for IntelMethodology and KeyFigure in tests/unit/organizations/test_intel_methodology.py — test IntelMethodology frozen creation with defaults, 3 preset configurations (Local PD: centrality only + ceiling 0.2, Fusion Center: centrality + temporal + ceiling 0.5, FBI: all True + ceiling 0.4), observation_ceiling Probability bounds. Test KeyFigure creation (id, name, organization_id, role, structural_importance default 0.5, is_singleton default False), frozen immutability.

### Implementation (GREEN Phase)

- [ ] T011 [US1] Create Organization base model, IntelMethodology, and KeyFigure in src/babylon/models/entities/organization.py — Organization base with 16 fields per data-model.md (NO internal_topology field — topology is emergent from COMMAND edges), ConfigDict(frozen=True), validators for headquarters_id-in-territory_ids and institutional_persistence-requires-is_institution. IntelMethodology with 5 fields + 3 class method presets (local_pd, fusion_center, fbi). KeyFigure with 6 fields.
- [ ] T012 [US1] Create 4 subtypes (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg) in src/babylon/models/entities/organization.py — each declares org_type as Literal[OrgType.X]. StateApparatus: jurisdiction, violence_capacity, surveillance_capacity, legal_authority list, intel_methodology with factory default. Business: sector, employment_count, surplus_extraction_rate, revenue. PoliticalFaction: ideology, is_player, relationship_to_player. CivilSocietyOrg: service_type, legitimacy. Create OrganizationType discriminated union using Annotated[Union[...], Field(discriminator="org_type")].
- [ ] T013 [US1] Create tests/unit/organizations/conftest.py with shared pytest fixtures — factory functions for all 4 Detroit subtypes (detroit_pd, ford_motor, revolutionary_workers_party, first_baptist_church per quickstart.md Scenarios 1-4), KeyFigure factory (pastor, deacons), IntelMethodology presets, minimal graph fixture with Territory nodes and SocialClass nodes for edge testing.
- [ ] T014 [US1] Extend src/babylon/models/entities/__init__.py with organization entity exports — add Organization, StateApparatus, Business, PoliticalFaction, CivilSocietyOrg, IntelMethodology, KeyFigure, OrganizationType to imports and __all__ list.
- [ ] T015 [US1] Add deprecation warning to src/babylon/models/components/organization.py — add `warnings.warn("OrganizationComponent is deprecated. Use Organization from babylon.models.entities.organization.", DeprecationWarning, stacklevel=2)` to OrganizationComponent.__init__ per research.md R8.
- [ ] T016 [US1] Extend src/babylon/models/world_state.py with organizations and key_figures dicts — add `organizations: dict[str, OrganizationType] = Field(default_factory=dict)` and `key_figures: dict[str, KeyFigure] = Field(default_factory=dict)`. Extend to_graph() to serialize org nodes with `_node_type="organization"` and key_figure nodes with `_node_type="key_figure"`. Extend from_graph() with dispatch for `_node_type=="organization"` (reconstruct via discriminated union) and `_node_type=="key_figure"`. Add `organization_excluded = {"effective_capacity", "composition_cache"}` exclusion set per research.md R9. Test with quickstart.md Scenario 9 (graph round-trip).

**Checkpoint**: All 4 subtypes instantiable, frozen, serializable. Detroit PD, Ford, RWP, First Baptist all work. Graph round-trip preserves all data.

______________________________________________________________________

## Phase 4: User Story 2 — Analyze Organization Composition (Priority: P2)

**Goal**: Three composition calculators (class, community, lifecycle) query membership edges and return proportional breakdowns.

**Independent Test**: Create an organization with known member distribution; verify all three composition queries return correct proportions per quickstart.md Scenarios 5-6.

### TDD Tests (RED Phase)

- [ ] T017 [US2] Write TDD tests for class, community, and lifecycle composition in tests/unit/organizations/test_composition.py — test class_composition with known MEMBERSHIP edge weights (quickstart.md Scenario 5: 500 industrial + 300 service + 50 petty_bourgeoisie = proportions summing to 1.0 ±0.01). Test community_composition with members in multiple hyperedges (proportions may sum > 1.0). Test lifecycle_composition with known D/P/D' distribution (quickstart.md Scenario 6: 200 youth + 600 adult + 200 elder = 0.2/0.6/0.2). Test empty membership returns empty distribution. Test hybrid membership aggregation (population-block edges + individual member_node_ids).

### Implementation (GREEN Phase)

- [ ] T018 [US2] Implement class_composition in src/babylon/organizations/composition.py — query MEMBERSHIP edges from org to SocialClass nodes, sum weights by class position, return CompositionResult with proportional distribution summing to 1.0. Handle both population-block edges and individual member_node_ids.
- [ ] T019 [US2] Implement community_composition and lifecycle_composition in src/babylon/organizations/composition.py — community_composition: for each member, query their XGI hyperedge memberships, aggregate proportionally (may sum > 1.0 since members belong to multiple communities). lifecycle_composition: for each member SocialClass node, read lifecycle_phase attribute, aggregate D/P/D' proportions summing to 1.0. Return CompositionResult for each.

**Checkpoint**: All 3 composition queries work. Scenario 5 and 6 from quickstart.md pass.

______________________________________________________________________

## Phase 5: User Story 3 — Consciousness Effect on Communities (Priority: P3)

**Goal**: Five-factor consciousness effect formula computes how organizations affect community consciousness.

**Independent Test**: Calculate consciousness delta for a revolutionary faction acting on a community; verify positive CI delta, REVOLUTIONARY tendency pressure, magnitude proportional to five-factor product per quickstart.md Scenario 7 and contracts/consciousness-effect-contract.md worked example.

### TDD Tests (RED Phase)

- [ ] T020 [US3] Write TDD tests for consciousness effect calculation in tests/unit/organizations/test_consciousness_effect.py — test five-factor formula: consciousness_delta = tendency_modifier × cadre_level × cohesion × credibility (action_base=1.0 Phase 1). Test REVOLUTIONARY tendency produces positive CI delta (quickstart.md Scenario 7: 0.15 × 0.7 × 0.6 × 0.5 = 0.0315). Test LIBERAL tendency produces negative CI delta (-0.05 × values). Test FASCIST tendency produces zero CI delta but FASCIST tendency_pressure. Test credibility derivation per subtype (CivilSocietyOrg→legitimacy, PoliticalFaction→0.5 default, StateApparatus→legal_standing mapping, Business→employment_share). Test short-circuit on zero cohesion/cadre/credibility. Test concurrent aggregation: sum CI deltas, dominant tendency = strongest weighted tendency, tie-breaking preserves current. Test Detroit worked example from contracts/consciousness-effect-contract.md (3 orgs, net +0.022, REVOLUTIONARY dominant).

### Implementation (GREEN Phase)

- [ ] T021 [US3] Implement derive_credibility per subtype in src/babylon/organizations/consciousness.py — CivilSocietyOrg returns org.legitimacy, PoliticalFaction returns defines.credibility_default_faction (0.5), StateApparatus maps legal_standing to credibility (SOVEREIGN→0.8, CHARTERED→0.6, else→0.5), Business computes employment_share from org.employment_count / community workforce (default 0.0 if unavailable).
- [ ] T022 [US3] Implement consciousness_effect and aggregate_consciousness_effects in src/babylon/organizations/consciousness.py — consciousness_effect: resolve tendency_modifier from defines, resolve credibility via derive_credibility, compute ci_delta = modifier × cadre_level × cohesion × credibility (FASCIST: ci_delta=0, tendency_pressure=FASCIST), return ConsciousnessDelta. aggregate_consciousness_effects: sum all ci_deltas, group by tendency_pressure and sum magnitudes, dominant = max weighted tendency (tie→no change), clamp new_ci to [0,1].

**Checkpoint**: Five-factor formula produces correct directional results. Scenario 7 and Detroit worked example pass.

______________________________________________________________________

## Phase 6: User Story 4 — State Intelligence Methodology (Priority: P4)

**Goal**: Three tiers of state intelligence (Local PD, Fusion Center, FBI) produce observably different capability profiles.

**Independent Test**: Create three StateApparatus organizations with different IntelMethodology presets; verify each has correct capabilities and observation ceiling per spec SC-004.

### TDD Tests (RED Phase)

- [ ] T023 [US4] Write TDD tests for 3-tier intelligence differentiation in tests/unit/organizations/test_intel_methodology.py (extend file from T010) — test that IntelMethodology.local_pd() produces centrality_analysis=True, all others False, ceiling=0.2. Test IntelMethodology.fusion_center() produces centrality+temporal=True, ceiling=0.5. Test IntelMethodology.fbi() produces all True, ceiling=0.4. Test that ceiling values match OrganizationDefines (not hardcoded). Test that three tiers are observably different (different bool combinations, different ceilings).

### Implementation (GREEN Phase)

- [ ] T024 [US4] Implement IntelMethodology preset class methods that read from OrganizationDefines in src/babylon/models/entities/organization.py — local_pd(defines), fusion_center(defines), fbi(defines) class methods that construct IntelMethodology with correct boolean capabilities and ceiling values from defines.observation_ceiling_* parameters (not hardcoded). This may already be partially done in T011; this task ensures the presets use defines and are tested.

**Checkpoint**: Three distinct intelligence tiers verified. SC-004 passes.

______________________________________________________________________

## Phase 7: User Story 5 — Key Figure Identification and Vulnerability (Priority: P5)

**Goal**: Topology classifier reads COMMAND edge subgraph; key figure identifier finds articulation points; cohesion loss on removal.

**Independent Test**: Build a STAR-pattern COMMAND subgraph; classify topology; identify center as singleton key figure; verify cohesion loss on removal per quickstart.md Scenario 8.

### TDD Tests (RED Phase)

- [ ] T025 [P] [US5] Write TDD tests for topology classification in tests/unit/organizations/test_topology_classifier.py — test STAR detection (one hub, N-1 leaves connected to hub), HIERARCHY detection (tree structure, N-1 edges, acyclic), MESH detection (near-complete graph, edge density > 0.6), CELL detection (multiple components linked by bridges/cutouts), empty org (no COMMAND edges → None), single node (→ None). Use NetworkX to build test graphs with COMMAND edges between KeyFigure node IDs.
- [ ] T026 [P] [US5] Write TDD tests for key figure identification and cohesion loss in tests/unit/organizations/test_key_figures.py — test STAR topology: center is sole articulation point, is_singleton=True, structural_importance > 0.8 (quickstart.md Scenario 8). Test CELL topology: only cutout nodes are key figures. Test MESH topology: no/few key figures. Test cohesion loss: removing one key figure reduces cohesion by cohesion_loss_per_key_figure (0.2), floor at min_cohesion_threshold (0.05). Test removal of ALL key figures leaves cohesion at floor.

### Implementation (GREEN Phase)

- [ ] T027 [US5] Implement classify_topology and identify_key_figures in src/babylon/organizations/topology.py — classify_topology(org_id, member_node_ids, graph): extract COMMAND edge subgraph for member nodes, compute undirected projection, classify by structural properties (STAR: single hub degree ≥ N-1; HIERARCHY: tree N-1 edges; MESH: density > threshold; CELL: multiple components with bridges). Return TopologyClassification. identify_key_figures(org_id, member_node_ids, graph): use nx.articulation_points() on undirected COMMAND projection, compute structural_importance as (components_after_removal - 1) / total_nodes, set is_singleton=True if no structural equivalent. Implement cohesion_loss_on_removal(org, removed_kf_ids, defines) returning new cohesion value clamped to min_cohesion_threshold.

**Checkpoint**: Topology classification and key figure identification work. Scenario 8 passes.

______________________________________________________________________

## Phase 8: User Story 6 — D-P-D' Lifecycle Capacity Constraints (Priority: P6)

**Goal**: Effective organizational capacity reflects lifecycle composition — adults full, elders reduced (~0.2), youth zero.

**Independent Test**: Create organizations with known lifecycle distributions; verify effective capacity matches SC-008 formula (70% adult + 20% elder + 10% youth = 0.7×1.0 + 0.2×0.2 + 0.1×0.0 = 0.74).

### TDD Tests (RED Phase)

- [ ] T028 [US6] Write TDD tests for effective capacity calculation in tests/unit/organizations/test_composition.py (extend file from T017) — test 100% adult = 1.0 capacity. Test 100% youth = 0.0 capacity. Test 100% elder = ~0.2 capacity (defines.elder_capacity_factor). Test mixed SC-008 example: 70% adult + 20% elder + 10% youth = 0.74. Test that elder_capacity_factor is read from OrganizationDefines (not hardcoded). Test zero membership returns 0.0 effective capacity.

### Implementation (GREEN Phase)

- [ ] T029 [US6] Implement effective_capacity calculator in src/babylon/organizations/composition.py — effective_capacity(lifecycle_result: CompositionResult, defines: OrganizationDefines) -> float: P-phase proportion × 1.0 + D'-phase proportion × defines.elder_capacity_factor + D-phase proportion × 0.0. Return float in [0, 1]. Uses lifecycle_composition result from US2 as input.

**Checkpoint**: Effective capacity correctly reflects lifecycle composition. SC-008 passes.

______________________________________________________________________

## Phase 9: User Story 7 — Legacy Model Unification (Priority: P7)

**Goal**: Migrate legacy faction and institution data to unified Organization subtypes with zero information loss.

**Independent Test**: Round-trip migrate all entities from factions.json and institutions.json; verify every entity is representable as an Organization subtype per research.md R8 mapping.

### TDD Tests (RED Phase)

- [ ] T030 [US7] Write TDD tests for legacy migration in tests/unit/organizations/test_migration.py — test F001 "National Revival Movement" → PoliticalFaction with consciousness_tendency=FASCIST. Test F003 "Revolutionary Workers Party" → PoliticalFaction with consciousness_tendency=REVOLUTIONARY. Test Inst002 "Policing" → StateApparatus. Test Inst003 "Mass Media" → CivilSocietyOrg(service_type=MEDIA). Test Inst004 "Labor Unions" → CivilSocietyOrg(service_type=LABOR). Test Inst001 "Systemic Racism" is DROPPED (not an organization per Constitution I.16). Test all 4 factions migrate. Test all 7 institutions migrate (6 to org subtypes, 1 dropped). Test OrganizationComponent deprecation warning fires on construction.

### Implementation (GREEN Phase)

- [ ] T031 [US7] Implement legacy migration functions in src/babylon/organizations/migration.py — migrate_faction(faction_data: dict) -> PoliticalFaction: map ideology, class_composition → class_character, consciousness_strategy. migrate_institution(inst_data: dict) -> Organization | None: dispatch by institution type (State→StateApparatus, Economic/Social/Cultural/Religious/Educational→CivilSocietyOrg/Business, "Systemic Racism"→None with documented rationale). migrate_all(factions_path, institutions_path) -> dict[str, OrganizationType]: batch migration returning org dict keyed by ID per research.md R8 mapping table.

**Checkpoint**: All legacy entities migrate correctly. SC-006 passes.

______________________________________________________________________

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Package exports, integration test, and final validation.

- [ ] T032 [P] Update src/babylon/organizations/__init__.py with all public exports — composition functions, consciousness functions, topology functions, migration functions, types. Follow the grouped import + __all__ pattern from src/babylon/economics/__init__.py.
- [ ] T033 Write integration test in tests/integration/test_organization_detroit.py — full Detroit scenario with all 4 subtypes, MEMBERSHIP edges, COMMAND edges, composition queries, consciousness effects, topology classification, key figure identification, graph round-trip. Cover all 9 quickstart.md scenarios in a single integration test module.
- [ ] T034 Run full test suite (mise run test:unit) and verify all new tests pass with zero regressions. Fix any import, type, or compatibility issues surfaced by existing tests.
- [ ] T035 Run type checker (mise run typecheck) on src/babylon/organizations/ and src/babylon/models/entities/organization.py. Fix any mypy strict-mode violations. Ensure all public functions have type annotations and return types.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS US2-US7 (models must exist first)
- **US2 (Phase 4)**: Depends on US1 (needs Organization model + graph integration)
- **US3 (Phase 5)**: Depends on US1 (needs Organization model + defines)
- **US4 (Phase 6)**: Depends on US1 (needs IntelMethodology model)
- **US5 (Phase 7)**: Depends on US1 (needs KeyFigure model + COMMAND edges)
- **US6 (Phase 8)**: Depends on US2 (needs lifecycle_composition)
- **US7 (Phase 9)**: Depends on US1 (needs Organization subtypes for migration target)
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    v
Phase 2 (Foundational)
    │
    v
Phase 3 (US1: Models) ─── BLOCKS ALL ───┐
    │                                     │
    ├──► Phase 4 (US2: Composition)       │
    │        │                            │
    │        └──► Phase 8 (US6: Lifecycle) │
    │                                     │
    ├──► Phase 5 (US3: Consciousness) [P] │
    ├──► Phase 6 (US4: Intel Methods) [P] │
    ├──► Phase 7 (US5: Key Figures)   [P] │
    └──► Phase 9 (US7: Migration)     [P] │
                                          │
Phase 10 (Polish) ◄──────────────────────┘
```

### Within Each User Story

1. TDD tests FIRST — must FAIL before implementation (RED)
2. Implementation makes tests pass (GREEN)
3. Refactor if needed
4. Commit after phase completion

### Parallel Opportunities

**After US1 completes**, these can run in parallel:
- US3 (Consciousness), US4 (Intel Methods), US5 (Key Figures), US7 (Migration)
- US2 must complete before US6 (lifecycle composition → effective capacity)

**Within Phase 2**, T004-T007 are all [P] (different files).

**Within US1**, T008-T010 are all [P] (different test files, RED phase).

**Within US5**, T025-T026 are [P] (different test files).

______________________________________________________________________

## Parallel Example: Phase 2 (Foundational)

```bash
# Sequential (same file):
T002: Write enum tests (RED)
T003: Implement enums (GREEN)

# Then parallel (different files):
T004: Create types.py          [P]
T005: Extend defines.py        [P]
T006: Extend defines.yaml      [P]
T007: Extend tests/constants.py [P]
```

## Parallel Example: After US1 Completes

```bash
# These can all run in parallel (different modules):
Phase 5 (US3): Consciousness effect    → consciousness.py
Phase 6 (US4): Intel methodology        → organization.py presets
Phase 7 (US5): Topology + key figures   → topology.py
Phase 9 (US7): Legacy migration         → migration.py
```

______________________________________________________________________

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (enums, types, defines)
3. Complete Phase 3: US1 — Instantiate All Organization Types
4. **STOP and VALIDATE**: All 4 subtypes work, graph round-trip works
5. This alone unblocks all downstream features

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Models) → 4 subtypes instantiable, graph integrated (MVP!)
3. US2 (Composition) → Membership queries work
4. US3 (Consciousness) → Ideological effects calculable
5. US4 (Intel) → Intelligence tiers differentiated
6. US5 (Key Figures) → Topology + vulnerability analysis
7. US6 (Lifecycle) → Capacity constraints reflect demographics
8. US7 (Migration) → Legacy data unified
9. Polish → Integration tested, exports clean, types verified

### Commit Strategy

Commit after each completed phase:
- Phase 1: `feat(031): Phase 1 setup — organization package scaffolding`
- Phase 2: `feat(031): Phase 2 foundational — enums, types, defines`
- Phase 3: `feat(031): Phase 3 US1 — organization models + graph integration`
- Phase 4: `feat(031): Phase 4 US2 — composition calculators`
- Phase 5: `feat(031): Phase 5 US3 — consciousness effect formula`
- Phase 6: `feat(031): Phase 6 US4 — intelligence methodology presets`
- Phase 7: `feat(031): Phase 7 US5 — topology classifier + key figures`
- Phase 8: `feat(031): Phase 8 US6 — lifecycle capacity constraints`
- Phase 9: `feat(031): Phase 9 US7 — legacy migration`
- Phase 10: `feat(031): Phase 10 polish — exports, integration test, validation`

______________________________________________________________________

## Notes

- TopologyType is EMERGENT — computed from COMMAND edges, never stored on Organization
- ClassCharacter has 6 values: BOURGEOIS, PETTY_BOURGEOIS, LABOR_ARISTOCRATIC, PROLETARIAN, LUMPEN, CONTESTED
- All frozen Pydantic models use ConfigDict(frozen=True); mutations via model_copy(update={})
- consciousness_effect action_base defaults to 1.0 in Phase 1; Phase 2 OODA will add per-action-type coefficients
- elder_capacity_factor (0.2) is a single scalar in Phase 1; Phase 2 adds per-action-type matrix
- Observation ceilings, tendency_modifiers, credibility defaults — all from OrganizationDefines, never hardcoded
- Follow existing test patterns: @pytest.mark.math for formulas, @pytest.mark.topology for graph ops, @pytest.mark.unit for models
