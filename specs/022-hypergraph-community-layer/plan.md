# Implementation Plan: Hypergraph Community Layer

**Branch**: `022-hypergraph-community-layer` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-hypergraph-community-layer/spec.md`

## Summary

Implement a dual-graph architecture adding XGI hyperedges for n-ary community membership alongside the existing NetworkX flow graph. Communities (NEW_AFRIKAN, TRANS, DISABLED, etc.) are represented as hyperedges connecting all members simultaneously. A new `CommunitySystem` runs before `SolidaritySystem` in the engine pipeline, handling: alpha-smoothed community state decay, solidarity potential computation from community overlap, threat score aggregation, and reproduction cost modification. Legal status escalation is one-way (only political struggle reverses it). Infrastructure decays without active maintenance.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), NetworkX 3.x (existing flow graph), XGI 0.10 (hypergraph — already in pyproject.toml)
**Storage**: In-memory via GraphProtocol + XGI Hypergraph. No new database tables. Community state persists via WorldState serialization.
**Testing**: pytest with existing marker system (@pytest.mark.unit, @pytest.mark.integration, @pytest.mark.topology)
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project — engine extension
**Performance Goals**: Community overlap matrix (1000 nodes x 50 hyperedges) computes in <10ms per tick. Solidarity potential lookups are O(1) from cached overlap matrix.
**Constraints**: No database I/O during tick (Constitution II.6). Hypergraph rebuild only on membership change events, not per-tick.
**Scale/Scope**: Detroit test case: ~100-1000 agent nodes, 8-20 community types, membership changes rare (between ticks only)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Compliance |
|-----------|--------|------------|
| II.7 Edges vs Hyperedges | PASS | Core purpose of this feature. NetworkX for flows, XGI for membership. Two separate data structures. |
| II.2 Primitives vs Derived | PASS | Community membership is a primitive (stored). Solidarity potential, threat score, overlap matrix are derived (computed). |
| II.3 NetworkX as Manifold | PASS | XGI extends the manifold with a membership topology layer. Flow graph unchanged. |
| II.6 State is Data, Engine is Transformation | PASS | CommunityState is frozen Pydantic. CommunitySystem is pure transformation. No DB I/O during tick. |
| II.4 Quantities vs Coefficients | PASS | Community state (heat, cohesion, infrastructure) are coefficients with alpha-smoothing. Solidarity potential is a quantity computed per tick. |
| III.1 No Magic Constants | PASS | Reproduction cost modifiers trace to academic literature (healthcare disparities, wage gap studies). Alpha-smoothing rate traceable to empirical autocorrelation. |
| III.4 Data Source Traceability | PASS | Community population estimates from Census/ACS (approved source). Reproduction modifiers from healthcare expenditure surveys. |
| III.5 Empirical vs Strategic | PASS | Community membership and reproduction modifiers from data. Solidarity edge creation from strategic intervention. Community overlap creates *potential*, not *actuality*. |
| VI.1 Material Base First | PASS | This feature adds community-modulated reproduction costs (material base) and solidarity potential (pre-condition for solidarity networks). Does not add repression mechanics that bypass economic dynamics. |
| VIII.9 Community as Pairwise Edge | PASS | This feature specifically implements the correct pattern: XGI hyperedges for community membership, not combinatorial pairwise NetworkX edges. |
| I.7 Quantitative → Qualitative | PASS | Community state changes are alpha-smoothed quantities. Legal status transitions are discrete qualitative events (enum changes). |
| I.8 Tragedy of Inevitability | PASS | Infrastructure decays without maintenance. No self-recovery. Communities require active organizing work. |

No violations. Gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/022-hypergraph-community-layer/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity definitions and relationships
├── quickstart.md        # Getting started guide
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   ├── enums.py                          # + CommunityType, LegalStatus, MembershipRole enums
│   └── entities/
│       ├── community.py                  # NEW: CommunityState, CommunityMembership models
│       └── social_class.py               # + community_memberships field on SocialClass
├── engine/
│   ├── simulation_engine.py              # + CommunitySystem in _DEFAULT_SYSTEMS (position 6)
│   ├── services.py                       # + community_hypergraph optional field
│   └── systems/
│       └── community.py                  # NEW: CommunitySystem (alpha-smoothing, solidarity potential, threat score)
├── formulas/
│   └── community.py                      # NEW: solidarity_potential, threat_score, infrastructure_decay formulas
└── config/
    └── defines.py                        # + CommunityDefines configuration

tests/
├── unit/
│   ├── models/
│   │   └── test_community_models.py      # NEW: CommunityState, CommunityMembership validation
│   ├── engine/systems/
│   │   └── test_community_system.py      # NEW: CommunitySystem unit tests
│   └── formulas/
│       └── test_community_formulas.py    # NEW: Formula unit tests
└── integration/
    └── test_community_integration.py     # NEW: Full pipeline integration tests
```

**Structure Decision**: Single project, engine extension pattern. New module `community.py` for models and system. Follows existing feature patterns (e.g., Feature 002 contradiction fields, Feature 021 capital volume).

## Complexity Tracking

No violations to justify. Constitution check passes cleanly.
