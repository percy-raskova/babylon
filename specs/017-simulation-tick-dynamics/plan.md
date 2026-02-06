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
    protocols.py          # TickSimulator protocol, TickInitializer protocol
    simulator.py          # DefaultTickSimulator (8-step pipeline)
    initializer.py        # DefaultTickInitializer (census data seeding)
    smoothing.py          # CoefficientSmoother (alpha-smoothing logic)
    crisis_detector.py    # ThresholdCrisisDetector (unemployment/profit-rate thresholds)
    derived_rates.py      # DerivedRateCalculator (r, OCC, e, Phi_aggregate)
    precarity.py          # PrecarityDeriver (class distribution -> U-6/PTER/NILF)

tests/unit/economics/tick/
    __init__.py
    conftest.py           # Mock calculators, stable/crisis fixtures
    test_types.py         # Pydantic model validation
    test_simulator.py     # Single-tick pipeline tests (US1, US2, US3)
    test_initializer.py   # Census data seeding tests
    test_smoothing.py     # Alpha-smoothing behavior tests (US5)
    test_crisis.py        # Crisis detection threshold tests
    test_derived.py       # Derived rate computation tests (US6)
    test_precarity.py     # Precarity derivation tests

tests/integration/economics/
    test_tick_integration.py  # Multi-tick validation (US4), full pipeline
```

**Structure Decision**: Extends the existing `src/babylon/economics/` package with a new `tick/` subpackage, following the same pattern as `dynamics/`, `melt/`, `gamma/`, and `throughput/` subpackages. Test structure mirrors source layout under `tests/unit/economics/tick/`.

## Design Decisions

### D1. Standalone TickSimulator vs Engine System

The TickSimulator is a standalone service in `economics/tick/`, NOT a System in the engine's System chain. The engine Systems operate on per-node graph mutations at weekly timescale; Feature 017 operates on county-level aggregate state at annual timescale. See research.md R2 for full rationale.

### D2. Protocol-Based Dependency Injection

All calculator dependencies are injected via constructor following the Protocol pattern established by Features 013-016. This enables clean mock substitution in tests:

```
TickSimulator Protocol:
    tick(state: SimulationTickState) -> SimulationTickState

DefaultTickSimulator(
    melt_calculator: MELTCalculator,
    basket_calculator: BasketVisibilityCalculator,
    gamma_calculator: GammaIIICalculator,
    capital_calculator: CapitalStockCalculator,
    throughput_calculator: ThroughputCalculator,
    transition_engine: ClassTransitionEngine,
    imperial_rent_calculator: ImperialRentCalculator,
    crisis_detector: CrisisDetector,
    coefficient_smoother: CoefficientSmoother,
    derived_rate_calculator: DerivedRateCalculator,
    precarity_deriver: PrecarityDeriver,
)
```

### D3. Immutable State Chain

SimulationTickState is frozen (Pydantic `ConfigDict(frozen=True)`). Each tick produces a NEW state instance. The tick function is pure: `tick(state_t) -> state_t_plus_1`. No side effects, no shared mutable state.

### D4. Initialization Separation

Initialization from census data is a separate concern from tick execution. `TickInitializer` handles the one-time seeding, while `TickSimulator` handles ongoing tick-to-tick evolution. This separation means the tick simulator never needs to handle NoDataSentinel -- that's an initialization concern.

### D5. Precarity Derivation Formulas

During simulation ticks, precarity indicators are derived from class state:
- `U-6 ≈ lumpen_share + precaritization_rate * proletariat_share`
- `PTER ≈ precaritization_rate * proletariat_share * 0.4`
- `NILF ≈ lumpen_share * 0.6`

Coefficients (0.4, 0.6) are configurable and traceable to BLS cross-tabulation ratios.

## Complexity Tracking

No constitution violations to justify.
