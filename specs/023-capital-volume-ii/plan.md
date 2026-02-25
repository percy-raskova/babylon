# Implementation Plan: Capital Volume II Integration

**Branch**: `023-capital-volume-ii` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-capital-volume-ii/spec.md`

## Summary

Add circulation dynamics to the Babylon simulation engine, modeling capital as a process (M-C-P-C'-M') rather than a static snapshot. This extends the existing ValueTensor4x3 (production, Volume I) with turnover time, fixed/circulating capital decomposition, reproduction schema balance conditions, inventory/realization tracking, circulation costs, and integrated crisis detection. The implementation layers new functionality on top of existing infrastructure (CapitalStockCalculator, TickDynamicsSystem, CrisisState) without modifying their contracts.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-018)
**Storage**: In-memory via GraphProtocol. No new database tables. Circulation state persists via CountyEconomicState in the graph bridge.
**Testing**: pytest with TDD (red-green-refactor), markers: `@pytest.mark.unit`, `@pytest.mark.math`
**Target Platform**: Linux (simulation engine)
**Project Type**: Single Python package (`src/babylon/economics/circulation/`)
**Performance Goals**: Must not measurably degrade annual tick performance (currently ~52 ticks/second with all systems)
**Constraints**: Frozen Pydantic models, GraphProtocol integration, NoDataSentinel pattern, no external dependencies beyond existing stack
**Scale/Scope**: ~10 source files, ~10 test files, ~22 functional requirements, targeting ~150+ test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | Turnover time amplifies Phi extraction — core imports faster turnover = more surplus. Feature models this correctly via annual_rate_of_surplus_value. |
| I.3 TRPF with Counter-Tendencies | PASS | Volume II crisis complements TRPF, runs in parallel (FR-022). Does not replace or merge. |
| I.5 Department III | PASS | Extended reproduction check (FR-013) includes Dept III. Reproduction gap reveals exploitation of reproductive labor. |
| I.7 Quantitative -> Qualitative | PASS | Continuous quantities (inventory days, liquidity ratio) trigger discrete quality transitions (NORMAL/OVERPRODUCTION/SUPPLY_CRISIS, replacement cycle position enums). |
| I.12 Catastrophe Surface | PASS | Crisis severity thresholds (NORMAL > 95%, RECESSION > 70%) are explicit fold crossings. |
| II.2 Primitives vs Derived | PASS | Stored: turnover profile days, capital in each form, inventory levels. Computed: turnovers_per_year, liquidity_ratio, annual_surplus, realization_rate. No derived quantities stored. |
| II.4 Quantities vs Coefficients | PASS | Capital distribution and inventory are quantities (flux per tick). Turnover profiles are coefficients (alpha-smooth, industry-level). |
| II.6 State is Data, Engine is Transformation | PASS | All new types are frozen Pydantic. Transitions computed by pure functions. No mutation. |
| III.1 No Magic Constants | PASS | Turnover profiles from BEA/Census. All threshold values stored in `defaults.py` as named constants with traceability comments. See Threshold Traceability section below. |
| III.4 Data Source Traceability | PASS | BEA Fixed Asset Tables and Census M3/QFR are within approved source categories. No new source types needed. |
| VIII Anti-Patterns | PASS | No violations. Circulation costs classification maintains productive/unproductive distinction (not scalar). |

**Gate result**: PASS (no violations)

## Project Structure

### Documentation (this feature)

```text
specs/023-capital-volume-ii/
├── spec.md                  # Feature specification
├── plan.md                  # This file
├── research.md              # Phase 0 output
├── data-model.md            # Phase 1 output
├── quickstart.md            # Phase 1 output
├── contracts/               # Phase 1 output
│   └── circulation_formulas.py
├── checklists/
│   └── requirements.md      # Spec quality checklist
└── tasks.md                 # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/economics/circulation/
├── __init__.py              # Package exports with __all__
├── types.py                 # All frozen Pydantic models
│   ├── CapitalForm (StrEnum)
│   ├── ReplacementCyclePosition (StrEnum)
│   ├── InventoryDiagnosis (StrEnum)
│   ├── CrisisSeverity (StrEnum)
│   ├── CircuitState
│   ├── TurnoverProfile
│   ├── AnnualSurplusValue
│   ├── FixedCapitalItem
│   ├── DepreciationFundState
│   ├── MoralDepreciation
│   ├── InventoryState
│   ├── ReproductionBalance
│   ├── ReproductionAnalysis
│   ├── RealizationCrisis
│   ├── DisproportionalityCrisis
│   ├── PureCirculationCosts
│   ├── TransportationValue
│   ├── CirculationCrisisAssessment
│   └── CirculationCrisisState
├── circuit.py               # FR-001 to FR-003: Circuit state transitions
├── turnover.py              # FR-004 to FR-007: Turnover time, annual surplus
├── fixed_circulating.py     # FR-008 to FR-011: Decomposition, depreciation
├── reproduction.py          # FR-012 to FR-014: Reproduction schema checks
├── inventory.py             # FR-015 to FR-017: Inventory, realization crisis
├── costs.py                 # FR-018 to FR-020: Circulation costs
├── crisis.py                # FR-021 to FR-022: Integrated crisis assessment
└── defaults.py              # Default turnover profiles by NAICS sector

src/babylon/economics/tick/
├── types.py                 # MODIFIED: Add circulation_state field to CountyEconomicState
├── system.py                # MODIFIED: Add circulation step to annual pipeline
└── graph_bridge.py          # MODIFIED: Serialize circulation state to tick_ attributes

src/babylon/formulas/
└── circulation.py           # Formula registry entries (if applicable)

tests/unit/economics/circulation/
├── conftest.py              # Shared fixtures, factories
├── test_types.py            # Model validation, computed fields, edge cases
├── test_circuit.py          # Circuit state transitions
├── test_turnover.py         # Turnover time, annual surplus value (Marx examples)
├── test_fixed_circulating.py # Depreciation, decomposition, moral depreciation
├── test_reproduction.py     # Simple + extended reproduction conditions
├── test_inventory.py        # Inventory diagnosis, realization crisis detection
├── test_costs.py            # Circulation costs, productive/unproductive classification
└── test_crisis.py           # Integrated crisis assessment
```

**Structure Decision**: New `circulation/` subpackage under `economics/`, following the established pattern of `gamma/`, `crisis/`, `melt/`. Modified existing tick system files to integrate the new step. Test structure mirrors source structure 1:1.

## Implementation Phases

### Phase 1: Types & Computed Fields (FR-001, FR-003, FR-004, FR-005, FR-009, FR-011, FR-015)

**Goal**: All frozen Pydantic models with computed fields. No business logic functions yet.

**Files**: `types.py`, `test_types.py`

**Verification**: `poetry run pytest tests/unit/economics/circulation/test_types.py -v` — all computed field edge cases pass.

### Phase 2: Turnover & Annual Surplus (FR-004, FR-005, FR-006, FR-007)

**Goal**: Turnover time decomposition and annual surplus value amplification.

**Files**: `turnover.py`, `defaults.py`, `test_turnover.py`

**Verification**: Marx's numerical examples pass (s/v=100%, 6 turnovers = 600% annual rate). Industry defaults resolve correctly.

### Phase 3: Fixed/Circulating Capital (FR-008, FR-009, FR-010, FR-011)

**Goal**: Decompose constant capital, track depreciation fund, model moral depreciation.

**Files**: `fixed_circulating.py`, `test_fixed_circulating.py`

**Verification**: Straight-line depreciation arithmetic correct. Replacement cycle positions classify correctly. Moral depreciation handles zero physical life.

### Phase 4: Circuit State Transitions (FR-001, FR-002, FR-003)

**Goal**: Capital form state machine (M→C→P→C'→M').

**Files**: `circuit.py`, `test_circuit.py`

**Verification**: Total capital invariant preserved (M+P+C = constant, modulo surplus in production). Form transitions respect turnover profile timing. Zero-capital edge case returns 0.0 ratios.

### Phase 5: Reproduction Schema (FR-012, FR-013, FR-014)

**Goal**: Inter-departmental balance conditions.

**Files**: `reproduction.py`, `test_reproduction.py`

**Verification**: Simple reproduction: balanced and imbalanced cases (5+ test scenarios per SC-003). Extended reproduction with Dept III. Disproportionality direction correct.

### Phase 6: Inventory & Realization (FR-015, FR-016, FR-017)

**Goal**: Inventory tracking, realization crisis detection from time series.

**Files**: `inventory.py`, `test_inventory.py`

**Verification**: Inventory diagnosis thresholds correct. Realization rate severity classification matches spec. Time series trend detection works for rising/falling/flat patterns.

### Phase 7: Circulation Costs (FR-018, FR-019, FR-020)

**Goal**: Productive/unproductive labor classification, transportation value.

**Files**: `costs.py`, `test_costs.py`

**Verification**: Total pure circulation costs sum correctly. Circulation burden ratio correct. Transport value ratio correct.

### Phase 8: Integrated Crisis Assessment (FR-021, FR-022)

**Goal**: Combined crisis detection, CirculationCrisisState composition.

**Files**: `crisis.py`, `test_crisis.py`

**Verification**: All three crisis types detected independently and in combination. Normal conditions produce no crisis flags.

### Phase 9: Tick System Integration

**Goal**: Wire circulation into the annual pipeline and graph bridge.

**Files**: Modified `tick/types.py`, `tick/system.py`, `tick/graph_bridge.py`

**Verification**: `mise run test:unit` passes (no regressions). Circulation state persists across ticks via graph bridge. System order tests updated.

### Phase 10: Package Exports & CI

**Goal**: `__init__.py` with `__all__`, mypy passes, full test suite green.

**Files**: `circulation/__init__.py`, any lint/type fixes

**Verification**: `mise run check` passes. `poetry run mypy src/babylon/economics/circulation/ --strict` clean.

## Key Design Decisions

### D1: Layering over replacement
New functionality layers ON TOP of existing CapitalStockCalculator, TickDynamicsSystem, and CrisisState. No existing contracts are modified beyond adding new fields to CountyEconomicState.

### D2: Annual pipeline sub-stepping
Circuit phase transitions are simulated within the annual pipeline call as sub-steps (similar to crisis detection's 4 quarterly evaluations), not as separate weekly tick handlers. This maintains the established temporal architecture.

### D3: Department II combination
For reproduction schema checks, Departments IIa (necessary consumption) and IIb (luxury consumption) are combined into a single Department II row by summing their c, v, s values. This matches Marx's two-department schema while preserving the existing four-department tensor.

### D4: Hardcoded defaults with Protocol injection
Initial turnover profiles use hardcoded industry-level defaults in `defaults.py`. A `TurnoverProfileSource` Protocol enables future data loader injection without modifying formula code.

### D5: Parallel crisis systems
`CirculationCrisisState` is a new field on `CountyEconomicState`, independent of `crisis_state` (TRPF). This preserves theoretical distinction and avoids coupling two different crisis mechanisms.

## Threshold Traceability (III.1 Compliance)

All threshold constants MUST be defined as named `Final` constants in `defaults.py` with traceability comments. No inline magic numbers in formula code.

| Constant | Value | Source / Rationale |
|----------|-------|-------------------|
| `OVERPRODUCTION_DAYS_THRESHOLD` | 60 | Census M3 historical: avg US manufacturing inventory-to-shipments ratio ~1.3 months (~40 days). 60 days = ~1.5x normal buffer, consistent with Marx Capital II Ch. 6 on abnormal stock formation. |
| `SUPPLY_CRISIS_DAYS_THRESHOLD` | 7 | Standard JIT manufacturing minimum buffer. Below 1 week of raw materials risks production stoppage. BLS Productivity data shows avg lead time ~5-10 days for domestic inputs. |
| `COMMODITY_OVERHANG_CRISIS` | 0.3 | When >30% of total capital is stuck in commodity form, the realization problem dominates. Derived from Marx Capital II Ch. 16-17: proportion of capital in circulation vs production. |
| `LIQUIDITY_CRISIS_RATIO` | 0.1 | When <10% of capital is liquid, the entity cannot purchase inputs for the next production cycle. From Marx Capital II Ch. 15: minimum money reserve for continuous reproduction. |
| `REALIZATION_RATE_NORMAL` | 0.95 | >95% realization = normal friction losses in exchange. |
| `REALIZATION_RATE_SLOWDOWN` | 0.85 | 85-95% = mild demand contraction. Consistent with NBER recession classification thresholds for industrial production decline. |
| `REALIZATION_RATE_RECESSION` | 0.70 | 70-85% = significant demand failure. Below 70% = full crisis (>30% of production unsold). |
| `REPLACEMENT_BOOM_RATIO` | 1.5 | Investment >150% of depreciation = capital expansion wave. BEA Fixed Asset Tables: historically, investment/depreciation > 1.5 correlates with boom phases. |
| `REPLACEMENT_EXPANSION_RATIO` | 1.0 | Investment = depreciation = simple reproduction of fixed capital. |
| `REPLACEMENT_MAINTENANCE_RATIO` | 0.7 | Investment < depreciation but above 70% = gradual disinvestment. Below 70% = active capital destruction. |

## Complexity Tracking

No constitution violations. No complexity justifications needed.
