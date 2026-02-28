# Implementation Plan: OODA Loop System

**Branch**: `032-ooda-loop-system` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/032-ooda-loop-system/spec.md`

## Summary

Implement organizational action resolution using OODA (Observe-Orient-Decide-Act) loops as the core mechanic governing how organizations interact with communities each tick. The system introduces a three-phase turn structure (Layer 0 automatic metabolism, Action Phase with dynamic initiative scoring, Layer 3 consequence propagation), 21 action types with consciousness side-effects, community-modified action costs, and lifecycle-weighted capacity. Integrates with SimulationEngine as a new `OODASystem` registered after existing systems, using GraphProtocol for all graph operations and EventBus for event publishing.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol via NetworkXAdapter), XGI 0.10 (hypergraph, existing via Feature 022/029)
**Storage**: In-memory via GraphProtocol. No new database tables. Organization OODA profiles stored as graph node attributes. Action results as tick events.
**Testing**: pytest with existing markers (`@pytest.mark.unit`, `@pytest.mark.math`, `@pytest.mark.integration`)
**Target Platform**: Linux (development/CI)
**Project Type**: Single Python package (`src/babylon/`)
**Performance Goals**: Single tick with 50 organizations should complete OODA resolution in <100ms. Initiative scoring is O(n) per organization per tick.
**Constraints**: All coefficients in GameDefines (FR-034). No hardcoded numeric literals in system logic. Per-tick consciousness delta clamped below configurable maximum (FR-019).
**Scale/Scope**: ~50 organizations per simulation, ~20 communities, ~21 action types. Detroit integration scenario as canonical test.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I.1 Settler-Colonial Frame** | PASS | Action types include ASSIMILATE (state vs marginalized communities). Contradiction pairs affect action costs (FR-022). Colonial axis is structural, not incidental. |
| **I.2 Imperial Rent** | PASS | Layer 0 automatic metabolism preserves existing surplus extraction. OODA system layers on top, does not replace economic base. |
| **I.4 George Jackson Bifurcation** | PASS | Initiative scoring encodes contingent state power, not absolute. Revolutionary orgs can seize initiative (FR-044). |
| **I.6 Solidarity as Edge Mode** | PASS | ORGANIZE actions trigger edge mode transitions (TRANSACTIONAL -> SOLIDARISTIC) in Layer 3 (FR-032). Edge types are qualitative transforms, not scalar changes. |
| **I.7 Quantitative -> Qualitative** | PASS | Initiative score is a quantitative float. Edge mode transitions are qualitative discrete events. Consciousness changes are small per-tick quantities that accumulate to qualitative tendency shifts. |
| **I.16 Organization vs Institution** | PASS | Org subtypes (Feature 031) already encode this. `is_institution` flag affects persistence. StateApparatus institutions have institutional initiative bonus. |
| **I.17 OODA Loop as Organizational Metabolism** | PASS | Direct implementation of this constitutional principle. OODA profile constrains action capacity per tick. Trade-offs (speed vs coherence, autonomy vs coordination) are explicitly modeled. |
| **I.18 Material-Ideological Distinction** | PASS | Actions have material effects (infrastructure, resources) AND ideological effects (consciousness delta). Community has both material basis and ideological dimension. Credibility scales ideological effects by material relationship (membership overlap). |
| **II.2 Primitives vs Derived** | PASS | OODAProfile stores primitives (sensor_latency, decision_mode, action_points). cycle_time and initiative_score are computed, never stored. |
| **II.5 AI Observes, Never Controls** | PASS | NPC action selection uses deterministic priority stub (FR-038). No AI in the loop for action resolution. |
| **II.6 State is Data, Engine is Transformation** | PASS | OODAProfile is frozen Pydantic data. OODASystem.step() is pure transformation. Actions produce new state via model_copy(). |
| **II.7 Edges vs Hyperedges** | PASS | Community consciousness effects target hyperedges (communities). Organization-to-class relationships use pairwise edges (MEMBERSHIP). Layer 3 aggregation respects the two-layer architecture. |
| **III.1 No Magic Constants** | PASS | All coefficients in GameDefines.ooda (FR-034). Action costs, cycle time weights, initiative bonus values, consciousness effect magnitudes — all named and configurable. |
| **III.5 Empirical vs Strategic** | PASS | Material conditions (Layer 0) from data. Strategic intervention (Action Phase) from organization decisions. Consciousness effects are the meeting point — material credibility scales ideological impact. |
| **V. Action Vocabulary** | CHECK | Spec defines 21 action types. Constitution defines 9 player verbs + 6 state verbs. Need to verify alignment — see research.md. |
| **VI.1 Material Base First** | PASS | Layer 0 (economic metabolism) runs first each tick, before any organizational actions. Material base determines action capacity and constraints. |
| **VIII.1 Solidarity as Scalar** | PASS | ORGANIZE triggers discrete edge mode transition (TRANSACTIONAL -> SOLIDARISTIC), not scalar increment. |

**Gate Result**: PASS (no violations). V. Action Vocabulary alignment requires research but is not a blocker.

## Project Structure

### Documentation (this feature)

```text
specs/032-ooda-loop-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── ooda-profile-contract.md
│   ├── initiative-scoring-contract.md
│   ├── action-resolution-contract.md
│   └── consciousness-effect-contract.md
├── checklists/
│   └── requirements.md  # Existing
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── engine/
│   ├── systems/
│   │   └── ooda.py                    # OODASystem — main system entry point
│   └── simulation_engine.py           # Register OODASystem in _DEFAULT_SYSTEMS
├── ooda/                              # NEW package — OODA domain logic
│   ├── __init__.py                    # Package exports with __all__
│   ├── types.py                       # OODAProfile, Action, ActionResult, ActionType enum,
│   │                                  #   InitiativeScore, ConsciousnessDelta extension,
│   │                                  #   ActionCostModifier, TurnResolution
│   ├── initiative.py                  # compute_initiative_score(), resolve_action_order()
│   ├── cycle_time.py                  # compute_cycle_time() from OODAProfile
│   ├── action_costs.py               # compute_action_cost(), apply_community_modifier()
│   ├── action_eligibility.py         # check_eligibility(), ELIGIBILITY_MAP
│   ├── action_effects.py             # resolve_action(), compute_consciousness_delta()
│   ├── layer0.py                     # process_layer0() — automatic economic metabolism
│   ├── layer3.py                     # process_layer3() — consequence propagation
│   └── npc_stub.py                   # select_npc_actions() — simple priority-based stub
├── config/
│   └── defines.py                     # Add OODADefines sub-model to GameDefines
├── models/
│   └── enums.py                       # Add new EventType values, ActionType enum
└── organizations/
    └── consciousness.py               # Extend with action_base multiplier (Phase 2 hook)

tests/
├── unit/
│   └── ooda/                          # NEW test directory
│       ├── __init__.py
│       ├── conftest.py                # OODA test fixtures, factory helpers
│       ├── test_types.py              # OODAProfile, Action, ActionResult model tests
│       ├── test_initiative.py         # Initiative scoring tests
│       ├── test_cycle_time.py         # Cycle time computation tests
│       ├── test_action_costs.py       # Action cost modifier tests
│       ├── test_action_eligibility.py # Eligibility check tests
│       ├── test_action_effects.py     # Action resolution + consciousness delta tests
│       ├── test_layer0.py             # Layer 0 automatic metabolism tests
│       ├── test_layer3.py             # Layer 3 consequence propagation tests
│       └── test_npc_stub.py           # NPC action selection tests
└── integration/
    └── test_ooda_detroit.py           # Detroit 4-org integration test (User Story 7)
```

**Structure Decision**: New `src/babylon/ooda/` package follows the established pattern (compare `src/babylon/organizations/`, `src/babylon/economics/lifecycle/`). Domain logic is separated from engine system registration. The `OODASystem` in `engine/systems/ooda.py` is a thin orchestrator that delegates to domain calculators in `ooda/`.

## Complexity Tracking

No constitution violations requiring justification. All design decisions align with existing patterns.
