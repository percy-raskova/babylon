# Implementation Plan: Capital Volume III Integration

**Branch**: `024-capital-volume-iii` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-capital-volume-iii/spec.md`

## Summary

Integrate Marx's Capital Volume III surplus value distribution theory into Babylon's economics pipeline. The feature adds a financial layer that decomposes surplus value into four competing claims (profit, interest, rent, taxes), models credit cycle dynamics and fictitious capital accumulation, tracks TRPF counter-tendencies, and provides value basis conversion (nominal/real/labor-time). Implementation follows the established Protocol + Default pattern with frozen Pydantic models, integrating into the TickDynamicsSystem pipeline and graph bridge.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-023), httpx (FRED API via existing FredAPIClient)
**Storage**: In-memory via GraphProtocol. No new database tables. National financial state persists via `NationalTickParameters` extension. County-level distribution persists via `CountyEconomicState` in the graph bridge. FRED/Z.1/Census data loaded via existing `FredAPIClient` + SQLite 3NF schema.
**Testing**: pytest with `@pytest.mark.math` (formulas), `@pytest.mark.unit` (types), `@pytest.mark.integration` (pipeline)
**Target Platform**: Linux server (existing)
**Project Type**: Single Python package (existing `src/babylon/economics/` layout)
**Performance Goals**: New financial calculations must not measurably increase per-tick latency (currently ~ms range for county-level computations)
**Constraints**: All new types frozen (`ConfigDict(frozen=True)`), constrained Babylon types (`Currency`, `Probability`, `Coefficient`), `NoDataSentinel` for missing data, threshold constants with data source traceability
**Scale/Scope**: ~3,200 counties, 1 national state, per-tick computation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | PASS | Counter-tendency #5 references existing `phi_hour`; no duplication |
| I.3 TRPF with Counter-Tendencies | PASS | Core purpose: model tendency AND 6 counter-tendencies separately |
| II.2 Primitives vs Derived | PASS | Store: interest rates, credit aggregates, rent data. Compute: distribution shares, financialization index, net counter-tendency |
| II.4 Quantities vs Coefficients | PASS | Interest rates, credit growth = quantities (flux). Credit cycle phase = coefficient (alpha-smooth). Crisis = discontinuous reset |
| II.6 State is Data, Engine is Transformation | PASS | All new types frozen Pydantic. Computation via pure functions. No DB I/O during tick |
| III.1 No Magic Constants | PASS | All thresholds traced to FRED, NBER, BEA, Census data sources |
| III.2 Falsifiability Required | PASS | Financialization index backtestable against 2008; credit cycle phases observable in FRED data |
| III.4 Data Source Traceability | PASS | Uses approved sources: FRED, Census/ACS, BEA. Z.1 Financial Accounts requires explicit addition |
| VI.1 Material Base First | PASS | Economic extraction (surplus distribution) before class formation effects |
| VI.3 Flag Scope Creep | PASS | Transformation problem explicitly out of scope; Trinity Formula deferred |

**New data source requiring addition**: Federal Reserve Financial Accounts (Z.1) — sectoral balance sheet data for fictitious capital stock. Constitution III.4 amendment needed.

## Project Structure

### Documentation (this feature)

```text
specs/024-capital-volume-iii/
├── plan.md              # This file
├── research.md          # Phase 0: design decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: developer onboarding
├── contracts/           # Phase 1: function signatures
│   ├── distribution_formulas.py
│   ├── credit_formulas.py
│   ├── rent_formulas.py
│   ├── counter_tendency_formulas.py
│   └── monetary_formulas.py
└── tasks.md             # Phase 2: (/speckit.tasks output)
```

### Source Code (repository root)

```text
src/babylon/economics/
├── distribution/              # NEW: Surplus value split (US1)
│   ├── __init__.py
│   ├── types.py              # SurplusValueDistribution, DebtAccumulation
│   ├── calculator.py         # DistributionCalculator protocol + default
│   └── data_sources.py       # BEA rent, IRS tax data protocols
├── credit/                    # NEW: Credit dynamics (US2, US3)
│   ├── __init__.py
│   ├── types.py              # InterestRateState, CreditState, FictitiousCapitalStock
│   ├── credit_cycle.py       # CreditCycleDetector protocol + default
│   ├── interest.py           # InterestCalculator protocol + default
│   └── data_sources.py       # FRED interest/credit, Z.1 protocols
├── rent/                      # NEW: Ground rent (US4)
│   ├── __init__.py
│   ├── types.py              # RentExtraction, HousingValueDecomposition
│   ├── calculator.py         # RentCalculator protocol + default
│   └── data_sources.py       # Census/ACS housing data protocol
├── counter_tendencies/        # NEW: TRPF counter-tendencies (US5)
│   ├── __init__.py
│   ├── types.py              # CounterTendencyStrength
│   └── calculator.py         # CounterTendencyCalculator protocol + default
├── monetary/                  # NEW: Value basis conversion (US7)
│   ├── __init__.py
│   ├── types.py              # MonetaryAdjustment, ValueBasis enum
│   └── converter.py          # ValueBasisConverter protocol + default
├── financial_crisis/          # NEW: Integrated crisis (US6)
│   ├── __init__.py
│   ├── types.py              # FinancialCrisisAssessment, CreditCrisisIndicator
│   └── assessment.py         # FinancialCrisisAssessor protocol + default
├── tick/
│   ├── types.py              # EXTEND: NationalFinancialParameters, CountyEconomicState
│   ├── system.py             # EXTEND: New pipeline steps for financial layer
│   └── graph_bridge.py       # EXTEND: New tick_* attributes for financial state
└── data/fred/
    ├── api_client.py         # EXISTING: FredAPIClient (httpx-based)
    ├── loader_3nf.py         # EXTEND: Add interest rate and credit aggregate series
    └── z1_loader.py          # NEW: Fed Financial Accounts Z.1 parser

tests/unit/economics/
├── distribution/
│   ├── __init__.py
│   ├── conftest.py           # Mock data sources for distribution
│   ├── test_types.py         # SurplusValueDistribution model tests
│   └── test_calculator.py    # Distribution calculation tests
├── credit/
│   ├── __init__.py
│   ├── conftest.py           # Mock FRED/Z.1 data sources
│   ├── test_types.py         # CreditState, InterestRateState, FictitiousCapitalStock
│   ├── test_credit_cycle.py  # Credit cycle phase transitions
│   └── test_interest.py      # Interest rate bounds, burden calculation
├── rent/
│   ├── __init__.py
│   ├── conftest.py           # Mock Census/ACS data
│   ├── test_types.py         # RentExtraction, HousingValueDecomposition
│   └── test_calculator.py    # Rent decomposition, fictitious fraction
├── counter_tendencies/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_types.py
│   └── test_calculator.py    # Net tendency, correlation with profit rate
├── monetary/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_types.py
│   └── test_converter.py     # Round-trip consistency, basis conversion
└── financial_crisis/
    ├── __init__.py
    ├── conftest.py
    ├── test_types.py
    └── test_assessment.py    # Crisis cascade, integrated evaluation
```

**Structure Decision**: Follows established economics module pattern where each domain concern (distribution, credit, rent, counter-tendencies, monetary, financial crisis) is a separate package with `types.py`, calculator protocol + default implementation, and data source protocols. Mirrors `circulation/`, `crisis/`, `melt/`, `gamma/` package organization.
