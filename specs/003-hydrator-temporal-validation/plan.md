# Implementation Plan: Hydrator Temporal Validation & Deindustrialization Signals

**Branch**: `003-hydrator-temporal-validation` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-hydrator-temporal-validation/spec.md`

## Summary

Add temporal validation capabilities to MarxianHydrator including:

1. **Z-score anomaly detection** for flagging statistically unusual year-over-year changes in tensor components
1. **Deindustrialization signal detection** comparing Dept I trajectories between Wayne (Detroit core) and Oakland (affluent suburb) counties
1. **α-smoothing** for coefficient stabilization using exponentially weighted moving averages

The approach uses a tiered threshold system: Z-score with 5-year rolling baseline (primary) → empirical 95th percentile (fallback for \<5 years history) → 15% bootstrap threshold (initial calibration phase).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic 2.x (data validation), SQLAlchemy 2.x (QCEW data access), NumPy (statistics)
**Storage**: SQLite (`data/sqlite/marxist-data-3NF.sqlite` - QCEW fact tables)
**Testing**: pytest with markers (`@pytest.mark.integration`, `@pytest.mark.math`)
**Target Platform**: Linux (development), cross-platform (Poetry)
**Project Type**: Single (extends existing `src/babylon/economics/` module)
**Performance Goals**: α-smoothing adds \<10% overhead to tensor retrieval for 10-year series (SC-006)
**Constraints**: All thresholds must trace to empirical data or documented primitives (Constitution III.1)
**Scale/Scope**: Detroit metro test case (Wayne 26163, Oakland 26125, Macomb 26099), 2010-2022 time series

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle                               | Status  | Notes                                                                                                                                                                |
| --------------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **II.4 Quantities vs Coefficients**     | ✅ PASS | α-smoothing explicitly required by Constitution: "Coefficients transform slowly via α-smoothing"                                                                     |
| **III.1 No Magic Constants**            | ✅ PASS | k=2.5 traces to statistical theory (99% normal coverage); 5-year window traces to coefficient autocorrelation; fallback thresholds are empirically derived from data |
| **III.4 Data Source Traceability**      | ✅ PASS | All inputs trace to QCEW (labor hours by industry/county) per Constitution table                                                                                     |
| **IV Metro Detroit Test Case**          | ✅ PASS | Feature directly implements Wayne vs Oakland validation required by Constitution                                                                                     |
| **I.7 Quantitative→Qualitative**        | ✅ PASS | Anomaly flags are discrete events triggered by threshold crossing, not continuous gradation                                                                          |
| **VI.6 Constants Without Data Sources** | ✅ PASS | Bootstrap threshold (15%) is documented conservative estimate pending empirical calibration                                                                          |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/003-hydrator-temporal-validation/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output - existing code analysis
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - usage examples
├── contracts/           # Phase 1 output - interface contracts
│   └── temporal_validation.py  # Protocol definitions
├── checklists/
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/
├── hydrator.py          # EXISTING - MarxianHydrator class (extend)
├── tensor.py            # EXISTING - ValueTensor4x3 (no changes)
├── temporal/            # NEW - Temporal validation module
│   ├── __init__.py
│   ├── transitions.py   # TemporalTransition computation
│   ├── anomaly.py       # Z-score and threshold detection
│   ├── smoothing.py     # α-smoothed coefficient series
│   ├── signals.py       # Deindustrialization signal detection
│   ├── reports.py       # TemporalValidationReport generation
│   ├── annotations.py   # Analyst annotation management (FR-006)
│   └── validator.py     # TemporalValidator facade
└── calibration/         # NEW - Empirical calibration artifacts
    ├── __init__.py
    └── thresholds.py    # National 95th percentile threshold computation

tests/
├── integration/economics/
│   ├── test_hydrator.py           # EXISTING - extend with temporal tests
│   └── test_temporal_validation.py # NEW - integration tests
└── unit/economics/
    └── temporal/                   # NEW - unit test directory
        ├── test_transitions.py
        ├── test_anomaly.py
        ├── test_smoothing.py
        ├── test_signals.py
        ├── test_reports.py
        └── test_annotations.py
```

**Structure Decision**: Single project extending `src/babylon/economics/` with new `temporal/` submodule. This follows the existing pattern where `hydrator.py`, `tensor.py`, and related files coexist in the economics package.

## Complexity Tracking

> No Constitution Check violations requiring justification.

| Item                    | Status                                             |
| ----------------------- | -------------------------------------------------- |
| Constitution violations | None                                               |
| Complexity additions    | Standard - new submodule follows existing patterns |

______________________________________________________________________

## Phase 0: Research

### Existing Code Analysis

**MarxianHydrator** (`src/babylon/economics/hydrator.py`):

- 322 lines, fully implemented with 145 passing tests
- `hydrate(fips: str, year: int) -> ValueTensor4x3` - single-year hydration
- `hydrate_with_rent(core_fips, periphery_fips, year) -> Tuple[ValueTensor4x3, ValueTensor4x3, ImperialRent]`
- Uses SQLAlchemy queries against `fact_qcew_annual` table
- No temporal comparison functionality exists

**ValueTensor4x3** (`src/babylon/economics/tensor.py`):

- Pydantic model with 4 departments × 3 value components (c, v, s)
- Constrained types: `Currency`, `Coefficient`
- Properties: `total_v`, `profit_rate`, `dept_i_share`, etc.
- Immutable (frozen model)

**QCEW Data** (`data/sqlite/marxist-data-3NF.sqlite`):

- `fact_qcew_annual`: employment, wages by FIPS/year/NAICS
- `dim_county`: county metadata (FIPS, name, state)
- `dim_time_annual`: year dimension
- Coverage: 2010-2024 (loading via PRE-001)

### Dependencies

- NumPy: Required for Z-score computation (rolling std dev)
- Statistics module: Built-in, sufficient for basic percentile calculation
- No new external dependencies needed

### Risks

1. **Data availability**: Only 2021-2022 loaded - Z-score requires 5+ years. Mitigation: Fallback threshold system.
1. **NAICS reclassification**: 2017 NAICS revision may affect time series consistency. Mitigation: Document in test assertions.

______________________________________________________________________

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Key Entities** (from spec):

1. **TemporalTransition**: YoY change between consecutive tensors

   - fips_code, year_from, year_to
   - delta_total_v, delta_dept_shares, delta_profit_rate (percentages)
   - z_scores (dict by component), flags_raised (list)
   - detection_method: Z_SCORE | EMPIRICAL_THRESHOLD | BOOTSTRAP

1. **AnomalyThresholdConfig**: Detection configuration

   - z_score_k: float = 2.5
   - rolling_window_years: int = 5
   - empirical_percentile: int = 95
   - bootstrap_threshold: float = 0.15
   - national_p95_threshold: Optional[float] (computed from data)

1. **SmoothedCoefficientSeries**: α-smoothed time series

   - fips_code, coefficient_name, alpha
   - raw_values, smoothed_values, years (lists)

1. **DeindustrializationSignal**: Core vs suburb comparison

   - core_county, suburb_county (FIPS codes)
   - year_range, core_dept_i_trend, suburb_dept_i_trend (slopes)
   - signal_detected, signal_strength

1. **TemporalValidationReport**: Aggregate output

   - transitions, smoothed_series, signals, threshold_config

### Interface Contracts

See [contracts/temporal_validation.py](./contracts/temporal_validation.py) for Protocol definitions.

```python
class TemporalValidator(Protocol):
    """Protocol for temporal validation operations."""

    def compute_transition(
        self,
        fips: str,
        year_from: int,
        year_to: int
    ) -> TemporalTransition:
        """Compute YoY transition between consecutive years."""
        ...

    def detect_anomalies(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig
    ) -> list[TemporalTransition]:
        """Detect anomalous transitions across year range."""
        ...

    def smooth_coefficients(
        self,
        fips: str,
        years: Sequence[int],
        coefficient: str,
        alpha: float
    ) -> SmoothedCoefficientSeries:
        """Compute α-smoothed coefficient series."""
        ...

    def detect_deindustrialization(
        self,
        core_fips: str,
        suburb_fips: str,
        years: Sequence[int]
    ) -> DeindustrializationSignal:
        """Compare Dept I trajectories between core and suburb."""
        ...

    def generate_report(
        self,
        fips: str,
        years: Sequence[int],
        config: AnomalyThresholdConfig
    ) -> TemporalValidationReport:
        """Generate comprehensive validation report."""
        ...
```

### Quickstart

See [quickstart.md](./quickstart.md) for usage examples.

______________________________________________________________________

## Implementation Phases

### Phase A: Core Entities (Foundation)

- Implement Pydantic models for all 5 key entities
- Add constrained types (DetectionMethod enum)
- Unit tests for model validation

### Phase B: Transition Computation (FR-001)

- Implement `compute_transition()` method
- YoY percentage calculations for total_v, dept_shares, profit_rate
- Unit tests with known tensor pairs

### Phase C: Anomaly Detection (FR-002)

- Implement tiered threshold system
- Z-score computation with rolling window
- Fallback logic for insufficient history
- Unit tests for each detection method

### Phase D: α-Smoothing (FR-004)

- Implement EWMA computation
- Handle edge cases (single year, gaps)
- Verify α=0, α=1 boundary conditions
- Performance benchmark (\<10% overhead)

### Phase E: Deindustrialization Signal (FR-003, FR-005)

- Implement Dept I trajectory comparison
- Linear regression for trend slopes
- Signal strength calculation
- Integration tests with Wayne/Oakland data

### Phase F: Report Generation (FR-007)

- Combine all components into TemporalValidationReport
- Annotation support (FR-006)
- Integration tests

### Phase G: Calibration Artifact (FR-008)

- Compute national 95th percentile from available data
- Persist as calibration artifact
- Update on QCEW data ingestion

______________________________________________________________________

## Prerequisite Tracking

| ID      | Description                   | Status     | Blocking                                |
| ------- | ----------------------------- | ---------- | --------------------------------------- |
| PRE-001 | QCEW data ingestion 2010-2022 | ⏳ PENDING | Full validation (US1, US2 with Z-score) |

**Impact**: Phases A-D and basic Phase C (bootstrap threshold) can proceed. Phase E (deindustrialization signal) and Phase G (national calibration) are partially blocked pending data.
