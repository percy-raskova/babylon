# Demographics and Mortality: The Mass Line Refactor

## Overview

The Mass Line Refactor transforms the Babylon simulation from **Agent-as-Person** (1 agent = 1 individual) to **Agent-as-Block** (1 agent = 1 demographic block with population). This enables:

1. **Scalable Demographics**: Model populations without per-person agents
2. **Intra-Class Inequality**: Marginal workers can starve even when average wealth suffices
3. **Malthusian Dynamics**: Natural population equilibrium based on carrying capacity
4. **Grinding Attrition**: Probabilistic mortality replacing binary alive/dead checks

## Core Concepts

### Agent-as-Block Paradigm

Previously, each `SocialClass` entity represented a single person with binary survival (alive/dead). Now each entity represents a demographic block:

```python
class SocialClass:
    population: int = 1          # Block size (default=1 for backward compat)
    inequality: Gini = 0.0       # Intra-class inequality coefficient [0,1]
    wealth: Currency             # Total wealth of the block
    # ...
```

**Examples**:
- "The Detroit Working Class" - population=50,000, inequality=0.45
- "The Wall Street Bourgeoisie" - population=10,000, inequality=0.85

### The Inequality Coefficient (Gini)

The `inequality` field is a Gini coefficient [0, 1] measuring wealth distribution within the class:

| Value | Meaning | Effect |
|-------|---------|--------|
| 0.0 | Perfect equality | Coverage threshold = 1.0× (exact subsistence suffices) |
| 0.5 | Moderate inequality | Coverage threshold = 1.5× (50% surplus required) |
| 0.8 | High inequality | Coverage threshold = 1.8× (80% surplus required) |
| 1.0 | Maximum tyranny | Coverage threshold = 2.0× (impossible to prevent deaths) |

**Interpretation (Phase 3 Formula)**: The inequality coefficient determines how much **surplus coverage** is required to prevent ANY deaths:

```
threshold = 1.0 + inequality
```

At `inequality=0.8`:
- Coverage threshold = 1.8× subsistence needs
- Even with 1.5× coverage, deficit = 0.3, attrition occurs
- Requires 1.8× coverage to keep everyone alive

## The Grinding Attrition Formula

The VitalitySystem now implements three phases:

### Phase 1: The Drain (Population-Scaled)
Linear subsistence burn scaled by population:
```
cost = (base_subsistence × population) × subsistence_multiplier
wealth = max(0, wealth - cost)
```

A block of 100 workers burns 100× what a single worker burns.

### Phase 2: Grinding Attrition (Coverage Ratio Threshold)
Probabilistic mortality based on coverage deficit:

```python
# Step 1: Calculate coverage ratio
wealth_per_capita = wealth / population
subsistence_needs = s_bio + s_class
coverage_ratio = wealth_per_capita / subsistence_needs

# Step 2: Calculate threshold (increases with inequality)
threshold = 1.0 + inequality

# Step 3: Calculate attrition rate
if coverage_ratio >= threshold:
    attrition_rate = 0  # Everyone survives
else:
    deficit = threshold - coverage_ratio
    attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)

# Step 4: Calculate deaths
deaths = floor(population × attrition_rate)
population -= deaths
```

**Key insight**: High inequality raises the coverage threshold. With inequality=0.8, you need 1.8× subsistence coverage to prevent deaths, not just 1.0×.

### Phase 3: The Reaper (Extended)
Full extinction check:
- If `population = 0`: Mark `active = False`, emit `ENTITY_DEATH`
- If `population = 1` AND `wealth < consumption_needs`: Traditional binary death

## The Malthusian Correction

The formula creates natural equilibrium dynamics:

1. **Deaths occur** due to coverage deficit → population decreases
2. **Per-capita wealth increases** (same wealth, fewer people)
3. **Coverage ratio increases** → fewer future deaths
4. **Population stabilizes** at carrying capacity

**Key**: Wealth is NOT reduced when people die (the poor die with 0 wealth). This means per-capita wealth automatically rises for survivors.

**Example equilibrium** (inequality=0.5, subsistence_needs=0.01):
```
Tick 1: pop=1000, wealth=10, coverage=1.0, threshold=1.5 → deficit=0.5, deaths=500
Tick 2: pop=500,  wealth=10, coverage=2.0, threshold=1.5 → deficit=0, deaths=0
Equilibrium: coverage exceeds threshold, no more deaths
```

## Events

### POPULATION_ATTRITION (Phase 3)
Emitted when coverage deficit causes deaths:
```python
{
    "entity_id": "C001",
    "deaths": 500,
    "remaining_population": 500,
    "attrition_rate": 0.5
}
```

### ENTITY_DEATH
Emitted on full extinction (population = 0):
```python
{
    "entity_id": "C001",
    "wealth": 0.0,
    "consumption_needs": 0.01,
    "cause": "extinction"  # or "starvation" for single-person death
}
```

## Configuration

The Phase 3 formula uses direct mathematical relationships without tuning parameters:

- **Threshold**: `1.0 + inequality` (no configuration needed)
- **Attrition multiplier**: `0.5 + inequality` (built into formula)
- **base_subsistence**: From `GameDefines.economy.base_subsistence` (scaled by population)

The VitalityDefines section (`base_mortality_factor`, `inequality_impact`) is now unused in Phase 3.

## Backward Compatibility

Default values preserve old behavior:
- `population = 1`: Single-agent scenarios unchanged
- `inequality = 0.0`: Marginal wealth = average wealth (no grinding attrition)
- Phase 3 preserves binary death check for `population = 1`

Existing scenarios continue to work without modification.

## Usage Examples

### High-Inequality Urban Population
```python
urban_proletariat = SocialClass(
    id="C001",
    name="Los Angeles Working Class",
    role=SocialRole.PERIPHERY_PROLETARIAT,
    population=500000,
    inequality=0.65,
    wealth=25000.0,  # Total wealth
    s_bio=0.01,
)
# Per-capita: 0.05, Marginal: 0.0175, consumption: 0.01
# Some deaths expected due to inequality
```

### Low-Inequality Rural Community
```python
rural_commune = SocialClass(
    id="C002",
    name="Vermont Cooperative",
    role=SocialRole.PERIPHERY_PROLETARIAT,
    population=5000,
    inequality=0.15,
    wealth=500.0,
    s_bio=0.01,
)
# Per-capita: 0.1, Marginal: 0.085, consumption: 0.01
# No deaths - marginal wealth exceeds needs
```

## Population-Scaled Systems

The Mass Line paradigm extends beyond VitalitySystem to all systems that depend on population:

### ProductionSystem (The Soil)
Production scales linearly with population:
```python
produced_value = (base_labor_power * population) * bio_ratio
```

A demographic block of 1000 workers produces 1000× what a single worker produces. This models the collective labor power of a working class.

### MetabolismSystem (The Metabolic Rift)
Consumption scales linearly with population:
```python
total_consumption = (s_bio + s_class) * population
```

- Active entities consume resources proportional to their population
- **Inactive (dead) entities do not consume** - dead blocks don't eat
- This creates natural carrying capacity dynamics: overshoot triggers when population consumption exceeds biocapacity

### SurvivalSystem (The Calculus of Living) - Phase 4
P(Acquiescence) now uses per-capita wealth:
```python
wealth_per_capita = wealth / population if population > 0 else 0.0
p_acquiescence = calculate_acquiescence_probability(
    wealth=wealth_per_capita,  # Per-capita, not aggregate
    subsistence_threshold=threshold,
    steepness_k=k,
)
```

**Before Phase 4**: A block of 50,000 workers with $1000 total (aggregate) looked "wealthy" to the formula.

**After Phase 4**: The formula sees $0.02 per capita - correctly identifying an impoverished population unlikely to survive via acquiescence.

### Causal Chain
The systems interact in materialist causality order:
1. **VitalitySystem**: Deaths reduce population → per-capita wealth rises
2. **ProductionSystem**: Smaller population produces less total wealth
3. **MetabolismSystem**: Smaller population consumes less biocapacity
4. **SurvivalSystem**: Lower per-capita wealth → lower P(S|A)
5. **Equilibrium**: Population stabilizes at carrying capacity

### Per-Capita vs Aggregate Summary

| System | Metric | Treatment |
|--------|--------|-----------|
| VitalitySystem | Mortality | Per-capita (coverage ratio) |
| ProductionSystem | Output | Aggregate × population |
| MetabolismSystem | Consumption | Aggregate × population |
| SurvivalSystem | P(S\|A) | **Per-capita** (Phase 4) |

---

## Theoretical Basis

The Mass Line refactor implements key Marxist concepts:

1. **Primitive Accumulation**: High inequality reflects dispossession
2. **Reserve Army of Labor**: Deaths create downward wage pressure
3. **Crisis of Social Reproduction**: Marginal workers can't reproduce themselves
4. **Metabolic Rift**: Ecological limits manifest through population dynamics

The name "Mass Line" references the Maoist principle of learning from the masses - the simulation now models demographic blocks rather than abstract individuals.

## Files Modified

### Phase 1: Schema & VitalitySystem
| File | Change |
|------|--------|
| `src/babylon/models/types.py` | Added `Gini` constrained type [0,1] |
| `src/babylon/models/entities/social_class.py` | Added `population`, `inequality` fields |
| `src/babylon/config/defines.py` | Added `VitalityDefines` section |
| `src/babylon/models/enums.py` | Added `POPULATION_DEATH` event type |
| `src/babylon/engine/systems/vitality.py` | Implemented 3-phase vitality with initial formula |

### Phase 2: Production & Metabolism Scaling
| File | Change |
|------|--------|
| `src/babylon/engine/systems/production.py` | Scale production by `population` |
| `src/babylon/engine/systems/metabolism.py` | Scale consumption by `population`, skip inactive entities |

### Phase 3: Coverage Ratio Threshold Formula
| File | Change |
|------|--------|
| `src/babylon/systems/formulas/vitality.py` | NEW: `calculate_mortality_rate()` formula |
| `src/babylon/systems/formulas/__init__.py` | Export `calculate_mortality_rate` |
| `src/babylon/models/enums.py` | Added `POPULATION_ATTRITION` event type |
| `src/babylon/engine/systems/vitality.py` | Replaced formula, scale Drain by population |
| `tests/unit/formulas/test_vitality.py` | NEW: Formula unit tests |
| `tests/unit/engine/systems/test_demographic_dynamics.py` | NEW: System integration tests |
| `tests/constants.py` | Added `AttritionDefaults` constants |

### Phase 4: Survival Layer Normalization
| File | Change |
|------|--------|
| `src/babylon/engine/systems/survival.py` | P(S\|A) now uses `wealth_per_capita` |
| `tests/unit/engine/systems/test_survival.py` | NEW: Population normalization tests |

## See Also

- **ADR033**: Mass Line Refactor decision record
- **demographics-spec.yaml**: Original demographics specification
- **metabolic-slice.yaml**: Ecological limits and carrying capacity
