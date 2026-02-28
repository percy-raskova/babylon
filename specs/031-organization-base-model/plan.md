# Implementation Plan: Organization Base Model

**Branch**: `031-organization-base-model` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/031-organization-base-model/spec.md`

## Summary

Unified agent model for all organizations in Babylon. Organizations are the ONLY agents — everything else is substrate. Four subtypes (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg) share a frozen Pydantic base with type-specific extensions. Hybrid membership (population-block edges + individual Key Figure/cadre nodes). Five-factor consciousness effect formula. Sparrow-grounded intelligence methodology. Deprecates OrganizationComponent, faction.schema.json, institution.schema.json.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, discriminated unions), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph — existing via Feature 022/029)
**Storage**: In-memory via GraphProtocol. No new database tables. Organization state persists via WorldState serialization (`_node_type="organization"`). Key Figures as separate nodes (`_node_type="key_figure"`).
**Testing**: pytest with markers (unit, math, integration). TDD: red-green-refactor.
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project — simulation engine module
**Performance Goals**: < 10ms per organization per tick (cohort-level arithmetic, not agent-based simulation)
**Constraints**: Frozen Pydantic models (`ConfigDict(frozen=True)`), GraphProtocol compliance, no magic constants (III.1), all parameters traceable to data sources or exposed as tunable GameDefines
**Scale/Scope**: ~20-50 organizations per Detroit scenario. 4 subtypes, ~10 new enums, 1 new GameDefines category, 5 new EdgeType values, 3 composition calculators, 1 consciousness effect calculator, 1 key figure identifier.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.1 Settler-Colonial Frame | PASS | class_character distinguishes which class org serves; StateApparatus models settler-colonial enforcement |
| I.2 Imperial Rent (Φ) | PASS | Business.surplus_extraction_rate connects to Φ extraction chain |
| I.6 Solidarity as Edge Mode | PASS | Org edges use existing EdgeMode (EXTRACTIVE/SOLIDARISTIC/etc.) |
| I.7 Quantitative → Qualitative | PASS | cohesion/cadre_level are floats; topology_type is emergent classification from COMMAND edges; legal_standing is enum (discrete transforms) |
| I.16 Organization vs Institution | PASS | is_institution + institutional_persistence fields explicitly distinguish. Constitution: "Organization = voluntary coordination, can be destroyed. Institution = crystallized social relations." |
| I.17 OODA Loop | PASS | Explicitly deferred to Phase 2 in Scope Exclusions. action_base defaults to 1.0. |
| I.18 Material-Ideological Distinction | PASS | class_character = material basis; consciousness_tendency = ideological dimension. Gap between them = political struggle terrain. |
| II.2 Primitives vs Derived | PASS | Stores: cohesion, budget, membership edges (primitives). Computes: topology classification, composition, effective capacity, consciousness delta (derived). Topology is emergent from COMMAND edges — graph speaks the truth. |
| II.6 State is Data, Engine is Transformation | PASS | Frozen Pydantic models, model_copy() for mutations. |
| II.7 Edges vs Hyperedges | PASS | Org membership via NetworkX edges; community composition reads XGI hyperedge layer. Two layers remain separate. |
| III.1 No Magic Constants | PASS | All parameters tunable via OrganizationDefines. Observation ceilings, tendency_modifiers, elder capacity — all traceable. |
| III.4 Data Source Traceability | PASS | BLS (elder capacity), QCEW (employment), Sparrow 1991/1993 (intel methodology). |
| IV. Metro Detroit | PASS | SC-001 requires Detroit PD, Ford, revolutionary faction, mainstream church all instantiable. |
| VIII.6 Constants Without Data | PASS | All constants have provenance: BLS, QCEW, Sparrow. |
| VIII.9 Community as Pairwise Edge | PASS | Community composition reads XGI hyperedge membership, not pairwise edges. |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/031-organization-base-model/
├── plan.md                          # This file
├── research.md                      # Phase 0: resolved unknowns
├── data-model.md                    # Phase 1: entity definitions
├── quickstart.md                    # Phase 1: integration test scenarios
├── contracts/                       # Phase 1: system contracts
│   ├── organization-model-contract.md
│   └── consciousness-effect-contract.md
├── checklists/
│   └── requirements.md              # Spec quality checklist
└── tasks.md                         # Phase 2: /speckit.tasks output
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   ├── enums.py                     # EXTEND: OrgType, ClassCharacter, TopologyType,
│   │                                #   LegalStanding, JurisdictionLevel, ServiceType
│   │                                #   + 5 new EdgeType values
│   ├── entities/
│   │   ├── organization.py          # NEW: Organization base + 4 subtypes +
│   │   │                            #   IntelMethodology + KeyFigure
│   │   └── __init__.py              # EXTEND: export new org entities
│   ├── components/
│   │   └── organization.py          # DEPRECATE: add deprecation warning
│   └── world_state.py               # EXTEND: organizations dict, to/from_graph dispatch
├── config/
│   └── defines.py                   # EXTEND: OrganizationDefines category
├── organizations/                   # NEW MODULE: org-specific calculators
│   ├── __init__.py                  # Package exports
│   ├── types.py                     # ConsciousnessDelta, CompositionResult, TopologyClassification
│   ├── composition.py               # class/community/lifecycle composition
│   ├── consciousness.py             # Five-factor consciousness effect
│   ├── topology.py                  # Topology classifier + key figure identification
│   └── migration.py                 # Legacy schema migration
└── data/
    └── defines.yaml                 # EXTEND: organization section

tests/
├── unit/
│   └── organizations/
│       ├── conftest.py              # Org-specific fixtures
│       ├── test_organization_model.py
│       ├── test_subtypes.py
│       ├── test_enums.py
│       ├── test_composition.py
│       ├── test_consciousness_effect.py
│       ├── test_intel_methodology.py
│       ├── test_key_figures.py
│       ├── test_topology_classifier.py
│       └── test_migration.py
├── integration/
│   └── test_organization_detroit.py
└── constants.py                     # EXTEND: OrganizationBaseDefaults category
```

**Structure Decision**: New `src/babylon/organizations/` module for org-specific calculators, following the pattern of `src/babylon/economics/` for economics calculators. Models stay in `src/babylon/models/entities/` per existing convention. Enums extended in existing `enums.py` (no separate file).
