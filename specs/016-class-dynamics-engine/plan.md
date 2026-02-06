# Implementation Plan: Class Dynamics Engine

**Branch**: `016-class-dynamics-engine` | **Date**: 2026-02-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-class-dynamics-engine/spec.md`

## Summary

Implement a Class Dynamics Engine that models how class positions (LA, proletariat, lumpenproletariat) change over time through four transition pathways: accumulation (upward mobility), dispossession (downward via foreclosure/bankruptcy), precaritization (into lumpenproletariat), and stabilization (out of lumpenproletariat). The engine consumes economic conditions (wage, unemployment, imperial rent, dispossession rates) and produces updated class distributions while preserving the sum-to-one invariant. MVP uses hardcoded national dispossession averages by year with data source protocols for future extension, and a class-based step function for savings rates.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Feature 013 ClassPosition, NoDataSentinel from tensor.py)
**Storage**: In-memory computation; no new database tables. Reads from existing data sources via protocol pattern.
**Testing**: pytest with TDD (Red-Green-Refactor). Unit tests in `tests/unit/economics/dynamics/`. Markers: `@pytest.mark.unit`, `@pytest.mark.math`
**Target Platform**: Linux (development), CI/CD
**Project Type**: Single project - new subpackage under existing economics module
**Performance Goals**: Compute one county-year transition in <10ms (trivial for in-memory computation over ~3,200 US counties)
**Constraints**: All class shares non-negative and sum to 1.0 (hard invariant). Continuous flows only (no discrete jumps). Frozen Pydantic models for all result types.
**Scale/Scope**: ~3,200 US counties x annual computation. 9 source modules + 1 adapter + validation. ~100 unit tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | FR-008 integrates imperial rent as consumption subsidy affecting accumulation rate |
| I.5 Department III | PASS | Gamma visibility tensor (Feature 015) feeds into basket subsidy; not directly modified |
| I.7 Quantitative -> Qualitative | PASS | Continuous share flows (quantities) + threshold-based class position transitions (qualities). ClassPosition enum is discrete; shares are continuous |
| I.8 Tragedy of Inevitability | PASS | Dispossession mechanisms model downward mobility as default; upward mobility requires sustained conditions |
| II.2 Primitives vs Derived | PASS | Transition rates are derived from economic conditions (wage, unemployment, dispossession rates). Class shares are stored state. |
| II.4 Quantities vs Coefficients | PASS | Transition rates are coefficients (transform slowly); class shares are quantities (flux per tick) |
| II.6 State is Data, Engine is Transformation | PASS | ClassDistribution is frozen Pydantic model (data). ClassTransitionEngine transforms it (engine). No mutation of input. |
| III.1 No Magic Constants | PASS | Dispossession rates from federal data (Eviction Lab, US Courts, ATTOM). Savings rates from SCF. All traceable. |
| III.4 Data Source Traceability | PASS | Foreclosure: ATTOM/CoreLogic. Bankruptcy: US Courts. Eviction: Eviction Lab. Savings: Fed SCF. All in approved sources or justified additions. |
| III.5 Empirical vs Strategic | PASS | Class dynamics are material conditions (from data). Strategic intervention (solidarity, organizing) is NOT part of this feature. |
| VII.3 Determinism from Material Conditions | PASS | Transition rates constrain; they do not determine. Crisis amplification increases rates but doesn't force outcomes. |

**Constitution gate: PASS** - No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/016-class-dynamics-engine/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: developer quickstart
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/dynamics/
├── __init__.py              # Package exports with grouped __all__
├── types.py                 # ClassDistribution, EconomicConditions, TransitionRates, AccumulationResult, DispossessionRisk, SavingsRateSchedule
├── data_sources.py          # DispossessionDataSource, SavingsRateSource protocols
├── accumulation.py          # AccumulationCalculator protocol + DefaultAccumulationCalculator
├── dispossession.py         # DispossessionCalculator protocol + DefaultDispossessionCalculator
├── transition_engine.py     # ClassTransitionEngine protocol + DefaultClassTransitionEngine
├── crisis.py                # CrisisAmplifier protocol + DefaultCrisisAmplifier
├── hardcoded_data.py        # National average dispossession rates by year (2007-2020)
├── savings_schedule.py      # DefaultSavingsRateSchedule (class-based step function)
└── validation.py            # Three-tier validation for transition rates and class shares

tests/unit/economics/dynamics/
├── conftest.py              # Mock data sources, fixtures
├── test_types.py            # Frozen model tests, sum-to-one validation
├── test_accumulation.py     # Accumulation rate computation tests
├── test_dispossession.py    # Dispossession risk computation tests
├── test_transition_engine.py # Full transition simulation tests
├── test_crisis.py           # Crisis amplification tests
├── test_hardcoded_data.py   # Hardcoded data sanity checks
├── test_savings_schedule.py # Savings rate schedule tests
└── test_validation.py       # Three-tier validation tests
```

**Structure Decision**: Follows the established economics subpackage pattern from Features 013-015 (melt/, throughput/, gamma/). Each calculator follows the Protocol + DefaultImpl pattern with dependency injection. Data sources are protocol-based for future extensibility.

## Complexity Tracking

> No constitution violations detected. No complexity justifications needed.
