# Quickstart: Capital Volume III Integration

**Feature**: 024-capital-volume-iii | **Branch**: `024-capital-volume-iii`

## What This Feature Does

Adds a financial layer to Babylon's economics pipeline that models how surplus value is distributed among competing claimants (profit, interest, rent, taxes), tracks credit system dynamics and fictitious capital accumulation, monitors TRPF counter-tendencies, and supports value expression in multiple bases.

## Key Concepts

- **Surplus Distribution**: s = p + i + r + t (accounting identity)
- **Interest-Bearing Capital**: M → M' without production; bounded by profit rate
- **Fictitious Capital**: Financial claims valued by capitalization of expected income
- **Credit Cycle**: EXPANSION → OVEREXTENSION → CRISIS → RECOVERY (with STAGNATION shortcuts)
- **Counter-Tendencies**: 6 factors offsetting TRPF
- **Value Basis**: Nominal / Real / Labor-time conversion

## Architecture

```
National Level (1 per tick):
  InterestRateState ──► CreditState ──► FictitiousCapitalStock
       │                     │
       │                     └──► CreditCyclePhase
       │
       └──► CounterTendencyStrength, MonetaryAdjustment

County Level (per county per tick):
  SurplusValueDistribution ◄── national interest + county rent + county tax
       │
       ├── RentExtraction (agricultural, resource, urban)
       ├── HousingValueDecomposition (construction, rent, speculation)
       ├── DebtAccumulation (cumulative shortfall tracker)
       └── FinancialCrisisAssessment (integrated signals)
```

## How It Integrates

1. **Tick Pipeline**: New step between crisis detection (Step 5) and class transitions (Step 6) in `TickDynamicsSystem`
2. **Graph Bridge**: New `tick_*` prefixed attributes on territory nodes
3. **Data Sources**: Extends existing `FredAPIClient` + new Z.1 loader + Census/ACS housing loader
4. **Crisis Layer**: Financial crisis assessment feeds into existing `CrisisState` from Feature 018

## Running Tests

```bash
# All distribution tests
poetry run pytest tests/unit/economics/distribution/ -v

# All credit tests
poetry run pytest tests/unit/economics/credit/ -v

# All rent tests
poetry run pytest tests/unit/economics/rent/ -v

# All financial crisis tests
poetry run pytest tests/unit/economics/financial_crisis/ -v

# Full feature test suite
poetry run pytest tests/unit/economics/distribution/ tests/unit/economics/credit/ tests/unit/economics/rent/ tests/unit/economics/counter_tendencies/ tests/unit/economics/monetary/ tests/unit/economics/financial_crisis/ -v

# Type checking
poetry run mypy src/babylon/economics/distribution/ src/babylon/economics/credit/ src/babylon/economics/rent/ src/babylon/economics/counter_tendencies/ src/babylon/economics/monetary/ src/babylon/economics/financial_crisis/ --strict
```

## New Modules

| Module | Purpose | Key Types |
|--------|---------|-----------|
| `distribution/` | Surplus split: s → p + i + r + t | SurplusValueDistribution, DebtAccumulation |
| `credit/` | Interest rates, credit cycle, fictitious capital | InterestRateState, CreditState, FictitiousCapitalStock |
| `rent/` | Ground rent by category, housing decomposition | RentExtraction, HousingValueDecomposition |
| `counter_tendencies/` | 6 TRPF counter-tendencies | CounterTendencyStrength |
| `monetary/` | Value basis conversion | MonetaryAdjustment, ValueBasis |
| `financial_crisis/` | Integrated crisis assessment | FinancialCrisisAssessment, CreditCrisisIndicator |

## Data Sources

| Source | Series | Module |
|--------|--------|--------|
| FRED | FEDFUNDS, DGS10, BAA10Y | credit/data_sources.py |
| FRED | TCMDO, GFDEBTN, WILL5000PR | credit/data_sources.py |
| FRED | B230RC0Q173SBEA (rental income) | distribution/data_sources.py |
| FRED | A054RC1Q027SBEA (corporate tax) | distribution/data_sources.py |
| Fed Z.1 | Sectoral debt, equity, household debt | credit/data_sources.py |
| Census/ACS | B25077 (home values), B25064 (gross rent) | rent/data_sources.py |
| BLS | CPI, PPI for capital goods | monetary/data_sources.py |

## Dependencies

- Feature 011: ValueTensor4x3 (surplus value `s`)
- Feature 013: Imperial rent Phi (counter-tendency #5)
- Feature 017: TickDynamicsSystem pipeline + CountyEconomicState
- Feature 018: CrisisPhase, bifurcation risk
- Feature 023: CirculationCrisisState
