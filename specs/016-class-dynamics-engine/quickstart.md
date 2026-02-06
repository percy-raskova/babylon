# Quickstart: Class Dynamics Engine

**Feature**: 016-class-dynamics-engine
**Date**: 2026-02-05

## What This Feature Does

Models how class positions (labor aristocracy, proletariat, lumpenproletariat) change over time through four mechanisms:

1. **Accumulation** (Proletariat -> LA): Workers save enough wealth to cross the 50th percentile threshold
2. **Dispossession** (LA -> Proletariat): Foreclosure, bankruptcy, or medical debt destroys accumulated wealth
3. **Precaritization** (Proletariat -> Lumpen): Job loss pushes employed workers into labor market exclusion
4. **Stabilization** (Lumpen -> Proletariat): Gaining stable employment re-integrates excluded workers

## Quick Usage

```python
from babylon.economics.dynamics import (
    ClassDistribution,
    EconomicConditions,
    DefaultClassTransitionEngine,
    DefaultAccumulationCalculator,
    DefaultDispossessionCalculator,
    DefaultCrisisAmplifier,
    HardcodedNationalDispossessionSource,
    DefaultSavingsRateSchedule,
)

# 1. Create initial class distribution
dist = ClassDistribution(
    fips="26163",  # Wayne County (Detroit)
    year=2010,
    bourgeoisie_share=0.01,
    petit_bourgeoisie_share=0.09,
    labor_aristocracy_share=0.40,
    proletariat_share=0.35,
    lumpenproletariat_share=0.15,
)

# 2. Create economic conditions
conditions = EconomicConditions(
    fips="26163",
    year=2010,
    unemployment_rate=0.15,
    median_wage=35000.0,
    melt=62.0,
    phi_hour=3.50,
    foreclosure_rate=0.046,
    bankruptcy_rate=0.013,
    eviction_rate=0.070,
    crisis=True,
)

# 3. Build the engine with dependencies
dispossession_source = HardcodedNationalDispossessionSource()
savings_schedule = DefaultSavingsRateSchedule()
accumulation_calc = DefaultAccumulationCalculator(savings_schedule)
dispossession_calc = DefaultDispossessionCalculator(dispossession_source)
crisis_amp = DefaultCrisisAmplifier()

engine = DefaultClassTransitionEngine(
    accumulation_calculator=accumulation_calc,
    dispossession_calculator=dispossession_calc,
    crisis_amplifier=crisis_amp,
)

# 4. Simulate one period
new_dist = engine.simulate_transitions(dist, conditions)

# 5. Check results
print(f"LA: {dist.labor_aristocracy_share:.3f} -> {new_dist.labor_aristocracy_share:.3f}")
print(f"Prol: {dist.proletariat_share:.3f} -> {new_dist.proletariat_share:.3f}")
print(f"Lumpen: {dist.lumpenproletariat_share:.3f} -> {new_dist.lumpenproletariat_share:.3f}")
print(f"Sum: {sum(new_dist.dynamic_shares()) + new_dist.bourgeoisie_share + new_dist.petit_bourgeoisie_share:.4f}")
```

## Key Patterns

### Protocol + Default Implementation
Every calculator has a Protocol (for DI/testing) and a Default implementation:
- `AccumulationCalculator` / `DefaultAccumulationCalculator`
- `DispossessionCalculator` / `DefaultDispossessionCalculator`
- `ClassTransitionEngine` / `DefaultClassTransitionEngine`
- `CrisisAmplifier` / `DefaultCrisisAmplifier`

### NoDataSentinel for Missing Data
When data sources are unavailable, methods return `NoDataSentinel` instead of raising:
```python
result = engine.simulate_transitions(dist, conditions)
if isinstance(result, NoDataSentinel):
    print(f"Data unavailable: {result.reason}")
```

### Frozen Pydantic Models
All types are immutable. To update a distribution, create a new one:
```python
# WRONG: dist.labor_aristocracy_share = 0.38  # Raises ValidationError
# RIGHT: new_dist = dist.with_updated_dynamics(la=0.38, prol=0.36, lumpen=0.16)
```

### Three-Tier Validation
Transition rates and class shares are validated against Expected/Warning/Fail ranges:
```python
from babylon.economics.dynamics.validation import validate_transition_rates
valid, message = validate_transition_rates(rates)
# (True, None) -> expected
# (True, "WARNING: ...") -> unusual but valid
# (False, "FAIL: ...") -> invalid
```

## Module Layout

```
src/babylon/economics/dynamics/
├── __init__.py              # Public API
├── types.py                 # ClassDistribution, EconomicConditions, etc.
├── data_sources.py          # DispossessionDataSource protocol
├── accumulation.py          # Wealth accumulation calculation
├── dispossession.py         # Dispossession risk computation
├── transition_engine.py     # Main engine: distributions -> distributions
├── crisis.py                # Crisis amplification logic
├── hardcoded_data.py        # National averages by year (MVP)
├── savings_schedule.py      # Class-based savings rates
└── validation.py            # Three-tier validation
```

## Running Tests

```bash
# All dynamics tests
poetry run pytest tests/unit/economics/dynamics/ -v

# Specific test file
poetry run pytest tests/unit/economics/dynamics/test_transition_engine.py -v

# Type checking
poetry run mypy src/babylon/economics/dynamics/ --strict
```

## Dependencies

| Dependency | From | What We Use |
|------------|------|-------------|
| ClassPosition | Feature 013 (melt/types.py) | 5-class enum for savings schedule |
| NoDataSentinel | tensor.py | Data unavailability signaling |
| NationalParameters | Feature 013 (melt/parameters.py) | MELT, imperial rent values |
