# Implementation Plan: Capital Volume I Production Dynamics

**Branch**: `021-capital-volume-i` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-capital-volume-i/spec.md`

## Summary

Implement three production dynamics mechanisms from Marx's Capital Volume I: Reserve Army of Labor (wage discipline from unemployment), Primitive Accumulation/Dispossession Events (aggregate tracking of value transfers), and Working Day Classification (absolute vs. relative exploitation modes). Includes five data loaders for empirical calibration against the Detroit metro case study (Wayne, Oakland, Macomb counties, 2005-2020). Two new Systems (#17 ReserveArmySystem, #18 DispossessionEventSystem) integrate into the simulation engine's materialist causality pipeline. Reserve army wage pressure modifies `CountyEconomicState.median_wage` via a bounded sigmoid; dispossession events feed the existing Feature 016 class transition engine; working day visibility modifiers connect to consciousness dynamics.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models), NetworkX 3.x (graph), SQLAlchemy 2.x (ORM), SciPy (sigmoid optimization)
**Storage**: SQLite (marxist-data-3NF.sqlite for reference data); in-memory via GraphProtocol for simulation state
**Testing**: pytest with existing markers (math, unit, integration, topology)
**Target Platform**: Linux server (local simulation)
**Project Type**: Single project — extends existing `src/babylon/` package
**Performance Goals**: Reserve army computation < 1ms per territory per tick (16 territories typical)
**Constraints**: No DB I/O during tick execution (Constitution II.6); all constants must trace to data sources (III.1)
**Scale/Scope**: 3 counties (Detroit metro), 16 years (2005-2020), ~20 NAICS sectors

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | Reserve army is counter-tendency to TRPF via s/v; dispossession is intra-core Phi mechanism |
| I.3 TRPF + Counter-Tendencies | PASS | Reserve army models the wage-suppression counter-tendency separately from TRPF tendency |
| I.4 George Jackson Bifurcation | PASS | Dispossession events trigger LA→Proletariat transitions that feed bifurcation dynamics |
| I.7 Quantitative → Qualitative | PASS | Class position transitions are discrete events (enums), not continuous floats. ExploitationMode is an enum. |
| II.2 Primitives vs Derived | PASS | Reserve army counts (primitives) stored; wage_pressure (derived) computed. Tensor v from QCEW (primitive). |
| II.6 State is Data, Engine is Transformation | PASS | All models frozen Pydantic. Systems mutate graph in step(). No DB I/O during ticks. |
| III.1 No Magic Constants | PASS | Wage pressure sigmoid params (k, r0) in GameDefines. Dispossession weights configurable. |
| III.2 Falsifiability Required | PASS | FR-013 defines 3 falsifiable predictions. SC-001 requires negative correlation test. |
| III.4 Data Source Traceability | PASS | BLS, Eviction Lab, ATTOM/CoreLogic, Census all in approved sources (constitution III.4 table). |
| IV. Metro Detroit Test Case | PASS | All loaders target Wayne/Oakland/Macomb counties, 2005-2020. |
| VIII.6 Constants Without Data Sources | PASS | All weights and thresholds trace to BLS, Fed SCF, or Phillips curve literature. |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/021-capital-volume-i/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output (8 research decisions)
├── data-model.md        # Phase 1 output (6 entities, 5 fact tables)
├── quickstart.md        # Phase 1 output (architecture overview)
├── contracts/           # Phase 1 output (3 contracts)
│   ├── reserve_army_system.py
│   ├── dispossession_event_system.py
│   └── working_day_classifier.py
├── checklists/
│   └── requirements.md  # Quality checklist (all passing)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── economics/
│   ├── reserve_army/           # NEW: Reserve army module
│   │   ├── __init__.py
│   │   ├── types.py            # ReserveArmyState, ReserveArmyDynamics
│   │   ├── calculator.py       # DefaultWagePressureCalculator
│   │   └── data_sources.py     # ReserveArmyDataSource protocol + SQLite impl
│   ├── dispossession/          # NEW: Dispossession events module
│   │   ├── __init__.py
│   │   ├── types.py            # DispossessionEvent, TerritoryDispossessionState
│   │   ├── intensity.py        # DispossessionIntensityCalculator
│   │   └── data_sources.py     # TerritoryDispossessionDataSource protocol + SQLite impl
│   └── working_day/            # NEW: Working day module
│       ├── __init__.py
│       ├── types.py            # WorkingDayState, ExploitationMode
│       └── classifier.py       # DefaultWorkingDayClassifier
├── engine/
│   └── systems/
│       ├── reserve_army.py     # NEW: ReserveArmySystem (#17)
│       └── dispossession_events.py  # NEW: DispossessionEventSystem (#18)
├── config/
│   └── defines.py              # EXTEND: ReserveArmyDefines, DispossessionDefines, WorkingDayDefines
├── models/
│   └── enums.py                # EXTEND: DispossessionType, ExploitationMode, new EventTypes
├── data/
│   ├── bls_unemployment/       # NEW: BLS unemployment loader
│   │   └── loader.py
│   ├── eviction_lab/           # NEW: Eviction Lab loader
│   │   └── loader.py
│   ├── foreclosure/            # NEW: Foreclosure rate loader
│   │   └── loader.py
│   ├── census_housing/         # NEW: Census housing loader
│   │   └── loader.py
│   ├── bls_productivity/       # NEW: BLS productivity loader
│   │   └── loader.py
│   └── reference/
│       └── schema.py           # EXTEND: 5 new fact tables

tests/
├── unit/
│   ├── economics/
│   │   ├── reserve_army/       # Reserve army unit tests
│   │   ├── dispossession/      # Dispossession event unit tests
│   │   └── working_day/        # Working day unit tests
│   └── engine/
│       └── systems/
│           ├── test_reserve_army_system.py
│           └── test_dispossession_event_system.py
├── integration/
│   └── test_volume_i_integration.py  # Multi-tick feedback loop tests
└── unit/
    └── data/
        ├── test_bls_unemployment_loader.py
        ├── test_eviction_lab_loader.py
        ├── test_foreclosure_loader.py
        ├── test_census_housing_loader.py
        └── test_bls_productivity_loader.py
```

**Structure Decision**: Extends existing `src/babylon/economics/` package with three new subpackages following the Protocol + Default impl pattern established by Feature 016's dynamics module. Two new Systems follow the existing pattern in `src/babylon/engine/systems/`. Five new data loaders follow the `DataLoader` ABC pattern.
