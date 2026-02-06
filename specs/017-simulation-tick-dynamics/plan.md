# Implementation Plan: Simulation Tick Dynamics

**Branch**: `017-simulation-tick-dynamics` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-simulation-tick-dynamics/spec.md`

## Summary

Feature 017 integrates all prior economic calculators (Features 012-016) into a unified per-tick state evolution pipeline. The system operates in two modes: (1) initialization from census data (QCEW, BEA, ATUS, FRED/BLS) to seed initial state, and (2) simulation tick execution where the engine produces all county values deterministically. The core deliverable is a `TickSimulator` service that accepts `SimulationTickState` at year t and produces state at year t+1 via an 8-step dependency-ordered pipeline including national parameter computation, county-level economic state, class distribution transitions, and derived rate calculations. Alpha-smoothing provides stability for coefficients while quantities update directly.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-016)
**Storage**: In-memory computation; no new database tables. Reads from existing data sources via protocol pattern during initialization.
**Testing**: pytest with TDD (Red-Green-Refactor), existing test infrastructure (TestConstants, DomainFactory, economics conftest fixtures)
**Target Platform**: Linux server (existing deployment target)
**Project Type**: Single project, extending existing `src/babylon/economics/` package
**Performance Goals**: Single tick completes in under 5 seconds for 20-county MVP set
**Constraints**: Pure function (deterministic), forward-only (no prior-tick modification), sum-to-one invariant on class distributions
**Scale/Scope**: MVP: 10-20 representative US counties, 2010-2024 year range, ~8 new source files, ~6 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | Phi_aggregate computed per tick as sum of county phi_hour flows |
| I.3 TRPF with Counter-Tendencies | PASS | Derived profit rate tracked per tick; TRPF observable as trend (SC-007) |
| I.5 Department III | PASS | gamma_III (reproductive visibility) computed and smoothed per tick |
| II.2 Primitives vs Derived | PASS | Tick recomputes all derived quantities (r, OCC, e) from primitives per tick; never stores derived across ticks |
| II.4 Quantities vs Coefficients | PASS | Core design principle: quantities update directly, coefficients alpha-smooth (FR-005/FR-006) |
| II.5 AI Observes, Never Controls | PASS | No AI involvement; purely mechanical computation |
| II.6 State is Data, Engine is Transformation | PASS | SimulationTickState is immutable data; TickSimulator.tick() is pure transformation |
| III.1 No Magic Constants | PASS | All coefficients trace to data sources or are configurable with documented defaults |
| III.2 Falsifiability Required | PASS | Historical validation (SC-002) tests predictions against Fed SCF data |
| III.4 Data Source Traceability | PASS | All data sources listed: QCEW, BEA, ATUS, FRED/BLS, Fed SCF. FRED series for precarity indicators identified in research.md |
| V.1 Material Base First | PASS | Feature is purely material/economic computation |

**Post-Phase 1 Re-check**: All gates still pass. No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/017-simulation-tick-dynamics/
    plan.md              # This file
    spec.md              # Feature specification
    research.md          # Phase 0 research findings
    data-model.md        # Entity relationships and field definitions
    quickstart.md        # Usage patterns and module layout
    checklists/
        requirements.md  # Spec quality checklist
    tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/tick/
    __init__.py           # Public API exports
    types.py              # SimulationTickState, NationalTickParameters,
                          #   CountyEconomicState, SmoothedCoefficients,
                          #   TickSummary, DerivedRates
    system.py             # TickDynamicsSystem (System protocol, 8-step pipeline)
    initializer.py        # DefaultTickInitializer (census data seeding)
    smoothing.py          # CoefficientSmoother (alpha-smoothing logic)
    crisis_detector.py    # ThresholdCrisisDetector (unemployment/profit-rate thresholds)
    derived_rates.py      # DerivedRateCalculator (r, OCC, e, Phi_aggregate)
    precarity.py          # PrecarityDeriver (class distribution -> U-6/PTER/NILF)
    graph_bridge.py       # Read/write tick state from/to NetworkX graph

src/babylon/engine/services.py  # Extended with economics calculator fields

tests/unit/economics/tick/
    __init__.py
    conftest.py           # Mock calculators, stable/crisis fixtures, graph builders
    test_types.py         # Pydantic model validation
    test_system.py        # TickDynamicsSystem step() tests (US1, US2, US3)
    test_initializer.py   # Census data seeding tests
    test_smoothing.py     # Alpha-smoothing behavior tests (US5)
    test_crisis.py        # Crisis detection threshold tests
    test_derived.py       # Derived rate computation tests (US6)
    test_precarity.py     # Precarity derivation tests

tests/integration/economics/
    test_tick_integration.py  # Multi-tick validation (US4), engine integration
```

**Structure Decision**: Extends the existing `src/babylon/economics/` package with a new `tick/` subpackage and extends `src/babylon/engine/services.py` with economics calculator fields. The `TickDynamicsSystem` in `system.py` conforms to the engine's System protocol and is registered in `_DEFAULT_SYSTEMS`. A `graph_bridge.py` module handles reading/writing tick state from/to the shared NetworkX graph. Test structure mirrors source layout under `tests/unit/economics/tick/`.

## Design Decisions

### D1. Engine System Integration (TickDynamicsSystem)

The tick dynamics pipeline is implemented as a `TickDynamicsSystem` conforming to the engine's System protocol (`step(graph, services, context) -> None`), registered in the `_DEFAULT_SYSTEMS` list in the materialist causality chain. This follows the principle that all simulation mechanics integrate through the existing engine infrastructure rather than building parallel systems.

**Position in causality chain**: After `ProductionSystem` (value creation) and before `ImperialRentSystem` (value extraction). The TickDynamicsSystem provides county-level economic context (capital stock, throughput, class distributions) that downstream Systems can consume from graph metadata.

**Timescale bridging**: The engine operates at weekly timescale (~52 ticks/year). The TickDynamicsSystem gates full pipeline execution to year boundaries (`context.tick % weeks_per_year == 0`). On intermediate ticks, the System provides cached annual results from graph metadata without re-executing the pipeline.

**Graph integration**: County-level state is stored in Territory nodes (via FIPS codes) and national parameters in graph metadata (`graph.graph["tick_dynamics"]`). This allows downstream Systems to access economics data through the standard graph interface. See research.md R2 for full rationale.

### D2. ServiceContainer Extension for Economics Calculators

The `ServiceContainer` is extended with economics calculator fields so that `TickDynamicsSystem` (and potentially other Systems) can access them via the standard dependency injection pattern. This follows the existing ServiceContainer pattern rather than introducing a separate DI mechanism.

```
ServiceContainer (extended fields):
    melt_calculator: MELTCalculator | None
    basket_calculator: BasketVisibilityCalculator | None
    gamma_calculator: GammaIIICalculator | None
    capital_calculator: CapitalStockCalculator | None
    throughput_calculator: ThroughputCalculator | None
    transition_engine: ClassTransitionEngine | None
    imperial_rent_calculator: ImperialRentCalculator | None
```

All new fields are optional (default `None`) to preserve backward compatibility -- existing tests and Systems that don't need economics calculators continue to work unchanged. The `ServiceContainer.create()` factory method accepts optional calculator parameters. Internal helpers (CrisisDetector, CoefficientSmoother, DerivedRateCalculator, PrecarityDeriver) are owned by `TickDynamicsSystem` directly, not injected via ServiceContainer, as they are not shared across Systems.

### D3. Dual State Representation

SimulationTickState remains a frozen Pydantic model (`ConfigDict(frozen=True)`) for initialization and testing contexts. Within the engine System chain, the equivalent state is stored in the shared graph: Territory nodes hold county economic state, and `graph.graph["tick_dynamics"]` holds national parameters, smoothed coefficients, and tick summary. The TickDynamicsSystem reads from and writes to the graph following the same in-place mutation pattern as all other Systems. For standalone use (historical validation, testing), the system also supports a pure function interface: `tick(state_t) -> state_t_plus_1`.

### D4. Initialization Separation

Initialization from census data is a separate concern from tick execution. `TickInitializer` handles the one-time seeding, while `TickSimulator` handles ongoing tick-to-tick evolution. This separation means the tick simulator never needs to handle NoDataSentinel -- that's an initialization concern.

### D5. Precarity Derivation Formulas

During simulation ticks, precarity indicators are derived from class state:
- `U-6 ≈ lumpen_share + precaritization_rate * proletariat_share`
- `PTER ≈ precaritization_rate * proletariat_share * 0.4`
- `NILF ≈ lumpen_share * 0.6`

Coefficients (0.4, 0.6) are configurable and traceable to BLS cross-tabulation ratios.

### D6. Precarity Handoff Rule

The first simulation tick overwrites initialized FRED/BLS precarity values (U-6, PTER, NILF) with values derived from class distribution (D5 formulas). There is no blending, weighted transition, or calibration step — the handoff is a clean overwrite. Rationale: initialization values seed the simulation from external data, but once the simulation is running, precarity must be endogenous (derived from class state) to maintain internal consistency. Blending would create a hybrid regime where precarity partially depends on external data and partially on internal state, violating the principle that simulation ticks are self-contained.

## Complexity Tracking

No constitution violations to justify.
