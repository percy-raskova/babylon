# Implementation Plan: Institution Base Model

**Branch**: `040-institution-base-model` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/040-institution-base-model/spec.md`

## Summary

Implement the Institution entity as a third layer between substrate (SocialClass, Territory, Community hyperedges) and agents (Organizations). Institutions are frozen Pydantic models stored as `_node_type="institution"` graph nodes, following the exact pattern established by Feature 031 (Organization) and Feature 039 (State Apparatus AI). The feature adds 5 new enums, 5 new entity models, 3 new EventType values, 3 pure functions, WorldState integration, and a data-driven defaults section in GameDefines. No per-tick system is created — only the data model and stateless functions.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models, validators), NetworkX 3.x (GraphProtocol), XGI 0.10 (community embeddedness queries)
**Storage**: In-memory via GraphProtocol. No new database tables. Institution state persists via WorldState serialization (`_node_type="institution"`).
**Testing**: pytest (unit tests for models, validators, pure functions; integration tests for graph round-trip)
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project (existing `src/babylon/` layout)
**Performance Goals**: Model instantiation and pure function calls must be sub-millisecond. No per-tick system overhead in Phase 1.
**Constraints**: Frozen Pydantic models only. No EventBus dependency. Pure functions return events as data.
**Scale/Scope**: Dozens to low hundreds of institutions per simulation run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.16 Organization vs Institution | PASS | Spec directly implements this principle — institutions as distinct entities that survive member turnover |
| I.17 OODA as Org Metabolism | PASS | Institutions do NOT run OODA loops; they modulate housed org OODA profiles via hints |
| I.18 Material-Ideological Distinction | PASS | Internal balance of forces captures material basis; class_inscription captures ideological dimension |
| II.4 Quantities vs Coefficients | PASS | Faction weights are quantities (flux per tick via update function); class_inscription changes on coefficient timescale (alpha-smoothed) |
| II.6 State is Data | PASS | Institution is frozen Pydantic, mutations via model_copy() |
| II.7 Edges vs Hyperedges | PASS | Institution embeddedness queries community hyperedges via XGI; institution-org relations are dyadic edges |
| III.1 No Magic Constants | PASS | All defaults from defines.yaml data file. Alpha smoothing rate configurable. |
| III.4 Data Source Traceability | N/A | No empirical data sources needed for model definition |
| V. Action Vocabulary | PASS | Structural selectivity maps existing ActionType values to cost modifiers |
| VI.1 Material Base First | PASS | Institutions have material infrastructure (budget, fixed_assets, legal_authorities) |
| VIII.7 Superstructure Before Base | PASS | Institution model captures material base, not just ideological superstructure |

**Post-Phase 1 re-check**: All gates still pass. Data model uses frozen Pydantic, pure functions, data-driven defaults. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/040-institution-base-model/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── institution_protocol.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Created by /speckit.tasks
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   ├── enums.py                          # +5 new enums (ApparatusType, SocialFunction, etc.)
│   ├── entities/
│   │   └── institution.py                # NEW: Institution, InternalBalanceOfForces,
│   │                                     #      ReproductionMechanism, InstitutionOrgRelation,
│   │                                     #      SpawningBlueprint
│   └── world_state.py                    # MODIFY: add institutions dict, to_graph/from_graph
├── config/
│   └── defines.py                        # MODIFY: add InstitutionDefines section
├── data/
│   └── defines.yaml                      # MODIFY: add institution defaults
├── institution/                          # NEW: pure functions module
│   ├── __init__.py
│   ├── balance.py                        # update_internal_balance()
│   ├── selectivity.py                    # structural_selectivity()
│   ├── ooda_effects.py                   # hegemonic_fraction_effect()
│   └── queries.py                        # community_embeddedness(), housed_orgs(), territory_footprint()
└── schemas/
    └── entities/
        └── institution.schema.json       # MODIFY: add deprecation notice

tests/
├── unit/
│   ├── models/
│   │   └── test_institution.py           # NEW: model validation, computed fields, invariants
│   └── institution/
│       ├── test_balance.py               # NEW: update_internal_balance tests
│       ├── test_selectivity.py           # NEW: structural_selectivity tests
│       ├── test_ooda_effects.py          # NEW: hegemonic_fraction_effect tests
│       └── test_queries.py               # NEW: graph query function tests
└── integration/
    └── test_institution_graph.py         # NEW: WorldState round-trip, graph integration
```

**Structure Decision**: Follows existing single-project layout. New `institution/` module for pure functions parallels the pattern of `ooda/` for OODA functions. Entity models in existing `models/entities/` directory. Enums appended to existing `models/enums.py`.
