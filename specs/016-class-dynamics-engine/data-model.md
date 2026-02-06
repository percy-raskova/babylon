# Data Model: Class Dynamics Engine

**Feature**: 016-class-dynamics-engine
**Date**: 2026-02-05

## Entities

### ClassDistribution

Five-class share distribution for a county-year. The primary state object of the dynamics engine.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips | str | 5 chars (FIPS) | County identifier |
| year | int | ge=2007, le=2030 | Calendar year |
| bourgeoisie_share | float | ge=0.0, le=1.0 | Top 1% wealth share (~0.01) |
| petit_bourgeoisie_share | float | ge=0.0, le=1.0 | 90th-99th percentile share (~0.09) |
| labor_aristocracy_share | float | ge=0.0, le=1.0 | 50th-90th percentile share (~0.40) |
| proletariat_share | float | ge=0.0, le=1.0 | Bottom 50% employed share (~0.35) |
| lumpenproletariat_share | float | ge=0.0, le=1.0 | Bottom 50% excluded share (~0.15) |

**Validation rules**:
- Sum of all five shares must equal 1.0 (within tolerance of 0.001)
- All shares must be non-negative
- Frozen (immutable) after construction

**Computed properties**:
- `dynamic_shares() -> tuple[float, float, float]`: Returns (LA, proletariat, lumpen) tuple for engine operations
- `total_share_check() -> bool`: Returns True if shares sum to 1.0 within tolerance
- `with_updated_dynamics(la, prol, lumpen) -> ClassDistribution`: Returns new distribution with updated dynamic shares, preserving bourgeoisie and petit-bourgeoisie

### EconomicConditions

Aggregate economic state for a county-year. Input to the transition engine.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips | str | 5 chars (FIPS) | County identifier |
| year | int | ge=2007, le=2030 | Calendar year |
| unemployment_rate | float | ge=0.0, le=1.0 | Local unemployment rate |
| median_wage | float | ge=0.0 | Median annual wage ($) |
| melt | float | gt=0.0 | MELT ($/labor-hour) from Feature 013 |
| phi_hour | float | ge=0.0 | Imperial rent per hour ($) from Feature 013 |
| foreclosure_rate | float | ge=0.0, le=1.0 | Annual foreclosure filing rate |
| bankruptcy_rate | float | ge=0.0, le=1.0 | Annual personal bankruptcy rate |
| eviction_rate | float | ge=0.0, le=1.0 | Annual eviction filing rate (renters) |
| crisis | bool | - | True if TRPF or exogenous crisis active |

**Validation rules**:
- All rates clamped to [0.0, 1.0]
- Frozen (immutable) after construction
- melt must be positive (division guard)

### TransitionRates

Sparse transition structure for the three dynamic classes.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips | str | 5 chars (FIPS) | County identifier |
| year | int | ge=2007, le=2030 | Calendar year |
| dispossession | float | ge=0.0, le=1.0 | LA -> Proletariat rate |
| accumulation | float | ge=0.0, le=1.0 | Proletariat -> LA rate |
| precaritization | float | ge=0.0, le=1.0 | Proletariat -> Lumpen rate |
| stabilization | float | ge=0.0, le=1.0 | Lumpen -> Proletariat rate |

**Validation rules**:
- All rates non-negative
- All rates <= 1.0 (cannot move more than 100% of a class in one period)
- Frozen (immutable) after construction

**Relationships**:
- Derived from EconomicConditions via DispossessionCalculator and AccumulationCalculator
- Applied to ClassDistribution via ClassTransitionEngine

### AccumulationResult

Computed wealth change rate for a given economic scenario.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| wage | float | ge=0.0 | Annual wage income ($) |
| consumption | float | ge=0.0 | Annual consumption ($) |
| savings_rate | float | ge=0.0, le=1.0 | Effective savings rate |
| phi_adjustment | float | ge=0.0 | Imperial rent savings boost |
| annual_accumulation | float | - | Net annual wealth change ($), may be negative |
| years_to_threshold | float | None or gt=0.0 | Years to reach LA wealth threshold (None if negative accumulation) |

**Validation rules**:
- Frozen (immutable) after construction
- annual_accumulation may be negative (wealth destruction)

### SavingsRateSchedule

Class-based step function for savings rates.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| rates | dict[str, float] | 5 entries | ClassPosition name -> base savings rate |
| phi_cap | float | ge=0.0, le=0.10 | Maximum imperial rent adjustment (default 0.05) |

**Default values** (calibrated against SCF data):

| ClassPosition | Base Rate | Source |
|---------------|-----------|--------|
| BOURGEOISIE | 0.38 | SCF top 1% |
| PETIT_BOURGEOISIE | 0.20 | SCF 90th-99th |
| LABOR_ARISTOCRACY | 0.12 | SCF 50th-90th |
| PROLETARIAT | 0.03 | SCF bottom 50% |
| LUMPENPROLETARIAT | 0.00 | No savings capacity |

### DispossessionRisk

Composite risk assessment from multiple data sources.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| fips | str | 5 chars (FIPS) | County identifier |
| year | int | ge=2007, le=2030 | Calendar year |
| foreclosure_risk | float | ge=0.0, le=1.0 | Foreclosure probability |
| bankruptcy_risk | float | ge=0.0, le=1.0 | Bankruptcy probability |
| eviction_risk | float | ge=0.0, le=1.0 | Eviction probability |
| composite_risk | float | ge=0.0, le=1.0 | Weighted composite |
| foreclosure_available | bool | - | True if foreclosure data was available |
| bankruptcy_available | bool | - | True if bankruptcy data was available |
| eviction_available | bool | - | True if eviction data was available |

**Validation rules**:
- All risks clamped to [0.0, 1.0]
- Frozen (immutable) after construction

## Data Source Protocols

### DispossessionDataSource

```
get_foreclosure_rate(fips: str, year: int) -> float | None
get_bankruptcy_rate(fips: str, year: int) -> float | None
get_eviction_rate(fips: str, year: int) -> float | None
```

MVP implementation: `HardcodedNationalDispossessionSource` returns national averages (ignoring fips).

### SavingsRateSource

```
get_savings_rate(class_position: ClassPosition) -> float
get_phi_adjustment(phi_hour: float, wage: float) -> float
```

MVP implementation: `DefaultSavingsRateSchedule` returns class-based step function values.

## State Transitions

```
ClassDistribution(t) + EconomicConditions(t)
    |
    v
ClassTransitionEngine.simulate_transitions()
    |
    +-- AccumulationCalculator.compute() -> accumulation rate
    +-- DispossessionCalculator.compute() -> dispossession rates
    +-- CrisisAmplifier.amplify() (if crisis=True)
    |
    v
TransitionRates(t)
    |
    v
Rate Conversion (intermediate step):
    accumulation rate = min(annual_accumulation / wealth_threshold, max_rate)
        where wealth_threshold is the LA entry wealth level
        and max_rate caps at validation Warning upper bound (0.08)
    dispossession rate = DispossessionCalculator composite (see research.md §3a)
    precaritization rate = FR-015 formula from EconomicConditions
    stabilization rate = FR-016 formula from EconomicConditions
    |
    v
Apply flows:
    LA'     = LA     - dispossession*LA     + accumulation*Proletariat
    Prol'   = Prol   + dispossession*LA     - accumulation*Proletariat
                     - precaritization*Prol + stabilization*Lumpen
    Lumpen' = Lumpen + precaritization*Prol - stabilization*Lumpen
    |
    v
Normalize to sum=1.0
    |
    v
ClassDistribution(t+1)
```

## Relationship to Existing Types

| This Feature | Existing Type | Relationship |
|--------------|---------------|--------------|
| ClassDistribution.shares | ClassPosition (Feature 013) | Uses same 5-class taxonomy |
| EconomicConditions.melt | MELTCalculator (Feature 013) | Consumes MELT value |
| EconomicConditions.phi_hour | ImperialRentCalculator (Feature 013) | Consumes imperial rent |
| SavingsRateSchedule | NationalParameters (Feature 013) | May reference subsistence threshold |
| DispossessionRisk | NoDataSentinel (tensor.py) | Uses for unavailability signaling |
