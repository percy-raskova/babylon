# Tasks: Capital Volume III Integration

**Input**: Design documents from `/specs/024-capital-volume-iii/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This project uses TDD (per CLAUDE.md). Each user story phase includes RED phase tests before GREEN phase implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/babylon/economics/` (new packages: distribution, credit, rent, counter_tendencies, monetary, financial_crisis)
- **Tests**: `tests/unit/economics/` (matching package structure)
- **Tick integration**: `src/babylon/economics/tick/` (types.py, system.py, graph_bridge.py)
- **Data loaders**: `src/babylon/data/fred/` (existing FredAPIClient)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package directories, shared test infrastructure, and constitution prerequisite

- [ ] T001 Amend Constitution III.4 in `.specify/memory/constitution.md` to add Fed Z.1 Financial Accounts as approved data source (MUST precede any Z.1 protocol or loader work)
- [ ] T002 Create package directories for all six new modules: `src/babylon/economics/distribution/`, `src/babylon/economics/credit/`, `src/babylon/economics/rent/`, `src/babylon/economics/counter_tendencies/`, `src/babylon/economics/monetary/`, `src/babylon/economics/financial_crisis/`
- [ ] T003 [P] Create test package directories: `tests/unit/economics/distribution/`, `tests/unit/economics/credit/`, `tests/unit/economics/rent/`, `tests/unit/economics/counter_tendencies/`, `tests/unit/economics/monetary/`, `tests/unit/economics/financial_crisis/`
- [ ] T004 [P] Create `__init__.py` for all six new source packages with module docstrings per the `circulation/__init__.py` pattern
- [ ] T005 [P] Create `__init__.py` for all six new test packages

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared enums, threshold constants, and data source protocols that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Define `CreditCyclePhase` StrEnum (EXPANSION, OVEREXTENSION, CRISIS, RECOVERY, STAGNATION) in `src/babylon/economics/credit/types.py` following `CrisisPhase` pattern from `tick/types.py`
- [ ] T007 [P] Define `ValueBasis` StrEnum (NOMINAL, REAL, LABOR_TIME) in `src/babylon/economics/monetary/types.py`
- [ ] T008 [P] Define `RentCategory` StrEnum (AGRICULTURAL, RESOURCE, URBAN) in `src/babylon/economics/rent/types.py`
- [ ] T009 Define threshold constants with `Final[float]` and traceability docstrings in `src/babylon/economics/credit/types.py`: INTEREST_BURDEN_SQUEEZE, FINANCIALIZATION_BUBBLE, CREDIT_FRAGILITY_THRESHOLD, STAGNATION_CREDIT_GROWTH, OVEREXTENSION_DEFAULT_RATE, RECOVERY_CONSECUTIVE_PERIODS
- [ ] T010 [P] Define threshold constants in `src/babylon/economics/distribution/types.py`: DEBT_SPIRAL_THRESHOLD, DISTRIBUTION_EPSILON
- [ ] T011 [P] Define threshold constants in `src/babylon/economics/counter_tendencies/types.py`: COUNTER_TENDENCY_WEIGHTS (6-element list)
- [ ] T012 Define data source protocols in `src/babylon/economics/distribution/data_sources.py`: `RentalIncomeSource`, `TaxOnSurplusSource`, `InterestIncomeSource` per contracts/distribution_formulas.py
- [ ] T013 [P] Define data source protocols in `src/babylon/economics/credit/data_sources.py`: `InterestRateSource`, `CreditAggregateSource`, `Z1FinancialAccountsSource` per contracts/credit_formulas.py
- [ ] T014 [P] Define data source protocols in `src/babylon/economics/rent/data_sources.py`: `HousingDataSource`, `CountyRentalIncomeSource` per contracts/rent_formulas.py
- [ ] T015 [P] Define data source protocols in `src/babylon/economics/monetary/data_sources.py`: `PriceIndexSource` per contracts/monetary_formulas.py
- [ ] T016 Create shared test conftest with mock data sources in `tests/unit/economics/distribution/conftest.py` following `melt/conftest.py` pattern (MockRentalIncomeSource, MockTaxOnSurplusSource, MockInterestIncomeSource with realistic defaults)
- [ ] T017 [P] Create shared test conftest in `tests/unit/economics/credit/conftest.py` (MockInterestRateSource, MockCreditAggregateSource, MockZ1Source with realistic FRED-derived defaults)
- [ ] T018 [P] Create shared test conftest in `tests/unit/economics/rent/conftest.py` (MockHousingDataSource, MockCountyRentalIncomeSource with Census-derived defaults)
- [ ] T019 [P] Create shared test conftest in `tests/unit/economics/counter_tendencies/conftest.py`
- [ ] T020 [P] Create shared test conftest in `tests/unit/economics/monetary/conftest.py` (MockPriceIndexSource with CPI/deflator defaults)
- [ ] T021 [P] Create shared test conftest in `tests/unit/economics/financial_crisis/conftest.py`

**Checkpoint**: Foundation ready — all enums, thresholds, protocols, and mock data sources in place. User story implementation can begin.

______________________________________________________________________

## Phase 3: User Story 1 — Surplus Value Distribution Accounting (Priority: P1)

**Goal**: Decompose surplus value into p + i + r + t with accounting identity validation and debt accumulation tracking.

**Independent Test**: Provide known surplus value, verify distribution sums to total `s`, profit may go negative when claims exceed surplus.

### Tests for User Story 1

- [ ] T022 [P] [US1] RED: Write type tests for `SurplusValueDistribution` in `tests/unit/economics/distribution/test_distribution_types.py` — frozen model, computed fields (profit_of_enterprise, distribution_complete, financialization_share, rentier_share, claims_exceed_surplus), zero surplus, negative profit edge case, rent-alone-exceeds-surplus edge case
- [ ] T023 [US1] RED: Write type tests for `DebtAccumulation` in `tests/unit/economics/distribution/test_debt_accumulation.py` — frozen model, update method (profit < 0 increases debt, profit > 0 decreases debt, debt >= 0 invariant)
- [ ] T024 [P] [US1] RED: Write calculator tests in `tests/unit/economics/distribution/test_calculator.py` — compute_distribution returns valid distribution, accounting identity holds within EPSILON, zero surplus produces all-zero distribution, rising interest crowds out profit, claims exceeding surplus flags structural crisis, NoDataSentinel returned when data sources return None

### Implementation for User Story 1

- [ ] T025 [US1] GREEN: Implement `SurplusValueDistribution` and `DebtAccumulation` frozen Pydantic models in `src/babylon/economics/distribution/types.py` with computed fields per data-model.md
- [ ] T026 [US1] GREEN: Implement `DistributionCalculator` protocol and `DefaultDistributionCalculator` in `src/babylon/economics/distribution/calculator.py` per contracts/distribution_formulas.py — data-driven shares (interest from FRED, rent from BEA, taxes from IRS), profit as residual, NoDataSentinel for missing data
- [ ] T027 [US1] Update `src/babylon/economics/distribution/__init__.py` with grouped `__all__` exports (Types, Protocols, Default implementations)
- [ ] T028 [US1] REFACTOR: Verify all distribution tests pass, run `mypy --strict` on distribution module

**Checkpoint**: Surplus value distribution with accounting identity validation and debt tracking — independently testable with mock data.

______________________________________________________________________

## Phase 4: User Story 2 — Interest-Bearing Capital and Credit Dynamics (Priority: P1)

**Goal**: Model interest rate dynamics, credit cycle phase detection, and credit expansion/contraction.

**Independent Test**: Provide known profit rates and credit conditions, verify interest rate bounds and credit cycle phase transitions.

### Tests for User Story 2

- [ ] T029 [US2] RED: Write type tests for `InterestRateState` and `CreditState` in `tests/unit/economics/credit/test_credit_types.py` — frozen models, computed effective_rate, computed credit_fragility, field constraints
- [ ] T030 [P] [US2] RED: Write interest calculator tests in `tests/unit/economics/credit/test_interest.py` — compute_interest_rate_state from FRED data, county interest burden capped at profit rate (FR-003), zero profit rate yields zero interest, NoDataSentinel when FRED data unavailable
- [ ] T031 [P] [US2] RED: Write credit cycle detector tests in `tests/unit/economics/credit/test_credit_cycle.py` — all valid transitions (EXPANSION->OVEREXTENSION, OVEREXTENSION->CRISIS, CRISIS->RECOVERY, RECOVERY->EXPANSION, OVEREXTENSION->STAGNATION, RECOVERY->STAGNATION), reject invalid transitions, STAGNATION is terminal

### Implementation for User Story 2

- [ ] T032 [US2] GREEN: Implement `InterestRateState` and `CreditState` frozen Pydantic models in `src/babylon/economics/credit/types.py`
- [ ] T033 [US2] GREEN: Implement `InterestCalculator` protocol and `DefaultInterestCalculator` in `src/babylon/economics/credit/interest.py` — effective rate capped at county profit rate (FR-003)
- [ ] T034 [US2] GREEN: Implement `CreditCycleDetector` protocol and `DefaultCreditCycleDetector` in `src/babylon/economics/credit/credit_cycle.py` — directed state machine per FR-006 with transition validation
- [ ] T035 [US2] Update `src/babylon/economics/credit/__init__.py` with grouped `__all__` exports
- [ ] T036 [US2] REFACTOR: Verify all credit tests pass, run `mypy --strict` on credit module

**Checkpoint**: Interest rate modeling and credit cycle detection — independently testable with mock FRED data.

______________________________________________________________________

## Phase 5: User Story 3 — Fictitious Capital Accumulation (Priority: P2)

**Goal**: Track fictitious capital stock and compute financialization index.

**Independent Test**: Provide known debt/equity levels and real GDP, verify financialization ratio and overaccumulation signal.

**Dependency**: Requires US2 types committed (shares `credit/types.py`)

### Tests for User Story 3

- [ ] T037 [US3] RED: Write type tests for `FictitiousCapitalStock` in `tests/unit/economics/credit/test_fictitious_capital.py` — frozen model, computed total_claims (excludes derivatives), ratio_to_real method
- [ ] T038 [P] [US3] RED: Write calculator tests in `tests/unit/economics/credit/test_fictitious_capital_calc.py` — compute_fictitious_capital from Z.1 data, financialization_index = total_claims / real_gdp, overaccumulation signal when ratio exceeds FINANCIALIZATION_BUBBLE threshold, NoDataSentinel when Z.1 data unavailable

### Implementation for User Story 3

- [ ] T039 [US3] GREEN: Implement `FictitiousCapitalStock` frozen Pydantic model in `src/babylon/economics/credit/types.py`
- [ ] T040 [US3] GREEN: Implement `FictitiousCapitalCalculator` protocol and `DefaultFictitiousCapitalCalculator` in `src/babylon/economics/credit/fictitious_capital.py` — compute from Z.1 + FRED, financialization_index method
- [ ] T041 [US3] Update `src/babylon/economics/credit/__init__.py` with FictitiousCapitalStock and FictitiousCapitalCalculator exports
- [ ] T042 [US3] REFACTOR: Verify all fictitious capital tests pass, run `mypy --strict`

**Checkpoint**: Fictitious capital tracking with financialization index — independently testable.

______________________________________________________________________

## Phase 6: User Story 4 — Ground Rent Extraction (Priority: P2)

**Goal**: Decompose ground rent by category and housing value into construction/rent/speculation.

**Independent Test**: Provide known rental income and housing values, verify decomposition arithmetic and fictitious fraction.

### Tests for User Story 4

- [ ] T043 [US4] RED: Write type tests for `RentExtraction` in `tests/unit/economics/rent/test_rent_types.py` — frozen model, computed total_rent, rent_share_of_surplus method
- [ ] T044 [US4] RED: Write type tests for `HousingValueDecomposition` in `tests/unit/economics/rent/test_housing_types.py` — frozen model, computed market_price, fictitious_fraction
- [ ] T045 [P] [US4] RED: Write calculator tests in `tests/unit/economics/rent/test_calculator.py` — compute_rent_extraction from Census data, compute_rent_share (returns 0 for zero surplus), decompose_housing_value with construction/rent/speculation summing to market_price, NoDataSentinel when Census data unavailable

### Implementation for User Story 4

- [ ] T046 [P] [US4] GREEN: Implement `RentExtraction` frozen Pydantic model in `src/babylon/economics/rent/types.py`
- [ ] T047 [P] [US4] GREEN: Implement `HousingValueDecomposition` frozen Pydantic model in `src/babylon/economics/rent/types.py`
- [ ] T048 [US4] GREEN: Implement `RentCalculator` protocol and `DefaultRentCalculator` in `src/babylon/economics/rent/calculator.py`
- [ ] T049 [US4] GREEN: Implement `HousingDecompositionCalculator` protocol and `DefaultHousingDecompositionCalculator` in `src/babylon/economics/rent/calculator.py`
- [ ] T050 [US4] Update `src/babylon/economics/rent/__init__.py` with grouped `__all__` exports
- [ ] T051 [US4] REFACTOR: Verify all rent tests pass, run `mypy --strict` on rent module

**Checkpoint**: Ground rent decomposition and housing value analysis — independently testable.

______________________________________________________________________

## Phase 7: User Story 5 — Counter-Tendencies to TRPF (Priority: P3)

**Goal**: Track six counter-tendencies and compute net tendency strength indicator.

**Independent Test**: Provide indicator values for each counter-tendency, verify net calculation and correlation with profit rate.

### Tests for User Story 5

- [ ] T052 [P] [US5] RED: Write type tests for `CounterTendencyStrength` in `tests/unit/economics/counter_tendencies/test_types.py` — frozen model, computed net_counter_tendency, all six indicators
- [ ] T053 [P] [US5] RED: Write calculator tests in `tests/unit/economics/counter_tendencies/test_calculator.py` — compute from indicator values, positive net when counter-tendencies dominate, negative net when TRPF dominates, correlation check with profit rate direction, NoDataSentinel when indicator data unavailable

### Implementation for User Story 5

- [ ] T054 [P] [US5] GREEN: Implement `CounterTendencyStrength` frozen Pydantic model in `src/babylon/economics/counter_tendencies/types.py`
- [ ] T055 [US5] GREEN: Implement `CounterTendencyCalculator` protocol and `DefaultCounterTendencyCalculator` in `src/babylon/economics/counter_tendencies/calculator.py` — weighted sum of normalized indicators, imperial rent references existing phi_hour
- [ ] T056 [US5] Update `src/babylon/economics/counter_tendencies/__init__.py` with grouped `__all__` exports
- [ ] T057 [US5] REFACTOR: Verify all counter-tendency tests pass, run `mypy --strict`

**Checkpoint**: TRPF counter-tendency tracking — independently testable.

______________________________________________________________________

## Phase 8: User Story 6 — Integrated Financial Crisis Assessment (Priority: P3)

**Goal**: Integrate financial crisis indicators with existing production (Feature 018) and circulation (Feature 023) crisis assessments.

**Independent Test**: Provide production, circulation, and financial state, verify cascade detection (production -> circulation -> financial).

### Tests for User Story 6

- [ ] T058 [US6] RED: Write type tests for `FinancialCrisisAssessment` and `CreditCrisisIndicator` in `tests/unit/economics/financial_crisis/test_types.py` — frozen models, computed active_signals, crisis_probability, overproduction/profit_squeeze/liquidity_crisis flags
- [ ] T059 [P] [US6] RED: Write assessment tests in `tests/unit/economics/financial_crisis/test_assessment.py` — all three signals active, latent vulnerability (NORMAL production but rising financialization), cascade detection across phases, claims_exceed_surplus triggers structural crisis

### Implementation for User Story 6

- [ ] T060 [US6] GREEN: Implement `FinancialCrisisAssessment` and `CreditCrisisIndicator` frozen Pydantic models in `src/babylon/economics/financial_crisis/types.py`
- [ ] T061 [US6] GREEN: Implement `FinancialCrisisAssessor` protocol and `DefaultFinancialCrisisAssessor` in `src/babylon/economics/financial_crisis/assessment.py` — integrates profit squeeze, overaccumulation, credit fragility, claims_exceed_surplus
- [ ] T062 [US6] Update `src/babylon/economics/financial_crisis/__init__.py` with grouped `__all__` exports
- [ ] T063 [US6] REFACTOR: Verify all financial crisis tests pass, run `mypy --strict`

**Checkpoint**: Integrated financial crisis assessment — independently testable.

______________________________________________________________________

## Phase 9: User Story 7 — Inflation and Value Basis Conversion (Priority: P3)

**Goal**: Express economic values in nominal, real, and labor-time bases with round-trip consistency.

**Independent Test**: Provide CPI, deflator, and labor hours, verify conversions and round-trip consistency.

### Tests for User Story 7

- [ ] T064 [P] [US7] RED: Write type tests for `MonetaryAdjustment` in `tests/unit/economics/monetary/test_types.py` — frozen model, field constraints (cpi > 0, deflator > 0, snlt_per_dollar > 0)
- [ ] T065 [P] [US7] RED: Write converter tests in `tests/unit/economics/monetary/test_converter.py` — nominal_to_real, nominal_to_labor_time, real_to_nominal, round-trip consistency (nominal->real->nominal within EPSILON), SNLT computation (total_hours / nominal_gdp), NoDataSentinel when CPI/deflator data unavailable

### Implementation for User Story 7

- [ ] T066 [P] [US7] GREEN: Implement `MonetaryAdjustment` frozen Pydantic model in `src/babylon/economics/monetary/types.py`
- [ ] T067 [US7] GREEN: Implement `ValueBasisConverter` protocol and `DefaultValueBasisConverter` in `src/babylon/economics/monetary/converter.py`
- [ ] T068 [US7] Update `src/babylon/economics/monetary/__init__.py` with grouped `__all__` exports
- [ ] T069 [US7] REFACTOR: Verify all monetary tests pass, run `mypy --strict`

**Checkpoint**: Value basis conversion with round-trip consistency — independently testable.

______________________________________________________________________

## Phase 10: Data Loaders (Cross-Cutting)

**Purpose**: Concrete data loader implementations for FRED, Z.1, and Census/ACS

- [ ] T070 [P] RED: Write tests for FRED financial series loader in `tests/unit/data/fred/test_financial_series.py` — loading FEDFUNDS, DGS10, BAA10Y, TCMDO, GFDEBTN, WILL5000PR, B230RC0Q173SBEA, A054RC1Q027SBEA
- [ ] T071 [P] RED: Write tests for Z.1 Financial Accounts loader in `tests/unit/data/fred/test_z1_loader.py` — parsing corporate debt, household debt, derivatives notional
- [ ] T072 [P] RED: Write tests for Census/ACS housing data loader in `tests/unit/data/test_census_housing.py` — loading B25077 (home values), B25064 (gross rent)
- [ ] T073 GREEN: Extend `NATIONAL_SERIES` in `src/babylon/data/fred/api_client.py` with Volume III FRED series (FEDFUNDS, DGS10, BAA10Y, TCMDO, GFDEBTN, WILL5000PR, B230RC0Q173SBEA, A054RC1Q027SBEA)
- [ ] T074 GREEN: Extend `FredLoader` in `src/babylon/data/fred/loader_3nf.py` to load financial series into SQLite 3NF schema
- [ ] T075 GREEN: Implement `Z1Loader` in `src/babylon/data/fred/z1_loader.py` — parse Fed Financial Accounts bulk CSV, extract sectoral debt/equity totals per Z1FinancialAccountsSource protocol
- [ ] T076 GREEN: Implement Census/ACS housing data loader in `src/babylon/data/census/housing_loader.py` — load median home values, gross rent, construction cost index per HousingDataSource protocol
- [ ] T077 Implement concrete data source adapters connecting loaders to protocol interfaces in `src/babylon/economics/credit/data_sources.py`, `src/babylon/economics/distribution/data_sources.py`, `src/babylon/economics/rent/data_sources.py`, `src/babylon/economics/monetary/data_sources.py`
- [ ] T078 REFACTOR: Verify all data loader tests pass, run `mypy --strict` on data modules

**Checkpoint**: All data pipelines operational — FRED financial series, Z.1 accounts, Census housing.

______________________________________________________________________

## Phase 11: Tick System Integration (Cross-Cutting)

**Purpose**: Integrate all Volume III subsystems into the TickDynamicsSystem pipeline and graph bridge

- [ ] T079 RED: Write tests for `NationalFinancialParameters` in `tests/unit/economics/tick/test_financial_params.py` — frozen model containing InterestRateState, CreditState, FictitiousCapitalStock, CounterTendencyStrength, MonetaryAdjustment
- [ ] T080 RED: Write tests for extended `CountyEconomicState` in `tests/unit/economics/tick/test_county_state_ext.py` — new fields (surplus_distribution, rent_extraction, housing_decomposition, debt_accumulation, financial_crisis) with default factories
- [ ] T081 RED: Write graph bridge tests in `tests/unit/economics/tick/test_graph_bridge_financial.py` — new tick_* attributes written to territory nodes, read back correctly
- [ ] T082 RED: Write pipeline integration tests in `tests/unit/economics/tick/test_financial_pipeline.py` — financial layer step executes between crisis detection and class transitions, accounting identity holds post-pipeline
- [ ] T083 RED: Write three-stage crisis cascade scenario test in `tests/unit/economics/tick/test_crisis_cascade.py` — synthetically induce production crisis (Feature 018), then circulation crisis (Feature 023), then financial crisis (Feature 024), verify SC-009 cascade detection
- [ ] T084 GREEN: Define `NationalFinancialParameters` frozen Pydantic model in `src/babylon/economics/tick/types.py`
- [ ] T085 GREEN: Extend `CountyEconomicState` in `src/babylon/economics/tick/types.py` with surplus_distribution, rent_extraction, housing_decomposition, debt_accumulation, financial_crisis fields (all with default_factory)
- [ ] T086 GREEN: Add new tick_* attributes to `write_tick_state_to_graph` in `src/babylon/economics/tick/graph_bridge.py` — tick_interest_burden, tick_ground_rent, tick_rentier_share, tick_profit_of_enterprise, tick_financialization_share, tick_accumulated_debt, tick_claims_exceed_surplus, tick_housing_fictitious_fraction, tick_credit_cycle_phase, tick_financial_crisis_signals
- [ ] T087 GREEN: Add financial layer read-back to `read_tick_state_from_graph` in `src/babylon/economics/tick/graph_bridge.py`
- [ ] T088 GREEN: Add `_compute_financial_layer` pipeline step to `TickDynamicsSystem` in `src/babylon/economics/tick/system.py` — insert between Step 5 (crisis triggers) and Step 6 (class transitions), compute national financial params, then per-county distribution/rent/crisis assessment
- [ ] T089 REFACTOR: Verify all tick integration tests pass, run `mypy --strict` on tick module

**Checkpoint**: Full pipeline integration — Volume III financial layer executes within tick system, state persists via graph bridge.

______________________________________________________________________

## Phase 12: Polish and Cross-Cutting Concerns

**Purpose**: Documentation, validation, historical backtest

- [ ] T090 [P] Add three-tier validation (Expected/Warning/Fail) for financialization_index, interest_burden_ratio, and rentier_share in `src/babylon/economics/distribution/types.py` and `src/babylon/economics/credit/types.py`
- [ ] T091 [P] Write validation tests for three-tier ranges in `tests/unit/economics/distribution/test_validation.py` and `tests/unit/economics/credit/test_validation.py`
- [ ] T092 RED+GREEN: Write historical backtest for SC-004 in `tests/unit/economics/credit/test_historical_backtest.py` — verify financialization index identifies pre-2008 crisis preconditions using real FRED TCMDO/GDP time series data
- [ ] T093 Run full CI gate: `mise run check` — verify all new tests pass alongside existing 6900+ tests
- [ ] T094 Verify strict mypy passes on all new modules: `poetry run mypy src/babylon/economics/distribution/ src/babylon/economics/credit/ src/babylon/economics/rent/ src/babylon/economics/counter_tendencies/ src/babylon/economics/monetary/ src/babylon/economics/financial_crisis/ --strict`
- [ ] T095 Run quickstart.md validation — verify all test commands and module paths are correct

______________________________________________________________________

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately. Constitution amendment T001 MUST complete before Phase 2.
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phases 3-4 (US1, US2)**: Both P1 priority — can run in parallel after Phase 2 (different packages)
- **Phase 5 (US3)**: P2 priority — **depends on US2 completion** (writes to shared `credit/types.py`)
- **Phase 6 (US4)**: P2 priority — independent after Phase 2 (can run in parallel with US1/US2)
- **Phases 7-8 (US5, US7)**: P3 priority — independent after Phase 2
- **Phase 8 (US6)**: P3 priority — references types from US1-US4; best done after those complete
- **Phase 10 (Data Loaders)**: Can start after Phase 2; does not block user story types/calculators (mock data sufficient)
- **Phase 11 (Tick Integration)**: Depends on Phases 3-9 completion (needs all types and calculators)
- **Phase 12 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1** (Surplus Distribution): Independent after Phase 2
- **US2** (Credit Dynamics): Independent after Phase 2
- **US3** (Fictitious Capital): **Depends on US2** — writes to shared `credit/types.py`; cannot parallelize with US2
- **US4** (Ground Rent): Independent after Phase 2
- **US5** (Counter-Tendencies): Independent after Phase 2; references phi_hour from Feature 013
- **US6** (Financial Crisis): References types from US1-US4 — best done after those complete
- **US7** (Value Basis Conversion): Independent after Phase 2

### Within Each User Story

- RED tests MUST be written and FAIL before GREEN implementation
- Types before calculators
- Calculators before __init__.py exports
- REFACTOR after all tests pass

### Parallel Opportunities

- Phase 2: T006-T011 enums/constants all parallel; T012-T015 protocols all parallel; T016-T021 conftest all parallel
- Phases 3+4: US1 and US2 can execute in parallel (different packages)
- Phase 5: US3 MUST wait for US2 types (shared credit/types.py)
- Phases 6+7+9: US4, US5, US7 can execute in parallel (different packages)
- Phase 10: All three data loader streams (FRED, Z.1, Census) can parallelize

______________________________________________________________________

## Parallel Example: User Story 1

```bash
# Launch RED tests in parallel (different files):
Task: "Write type tests for SurplusValueDistribution in tests/unit/economics/distribution/test_distribution_types.py"
Task: "Write calculator tests in tests/unit/economics/distribution/test_calculator.py"

# Then sequentially (same file as T022):
Task: "Write type tests for DebtAccumulation in tests/unit/economics/distribution/test_debt_accumulation.py"
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (including constitution amendment T001)
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (Surplus Distribution) — accounting identity established
4. Complete Phase 4: US2 (Credit Dynamics) — interest rates and credit cycle
5. **STOP and VALIDATE**: Both P1 stories functional with mock data
6. Commit and verify CI gate passes

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. US1 + US2 -> Core financial layer (MVP)
3. US3 (after US2) + US4 -> Fictitious capital + rent (P2 stories)
4. US5 + US6 + US7 -> Counter-tendencies + crisis integration + monetary (P3 stories)
5. Data Loaders -> Real FRED/Z.1/Census data
6. Tick Integration -> Full pipeline operational
7. Polish -> Validation, backtest, CI

______________________________________________________________________

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- RED phase tests MUST fail before GREEN implementation
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
- All new types MUST be frozen (`ConfigDict(frozen=True)`)
- All threshold constants MUST have traceability docstrings citing data sources
