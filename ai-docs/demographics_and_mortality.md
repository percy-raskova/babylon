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
| 0.0 | Perfect equality | Mean = Median, everyone survives if average does |
| 0.5 | Moderate inequality | Middle-class conditions |
| 1.0 | Maximum tyranny | Bottom majority has nothing, guaranteed deaths |

**Interpretation**: The inequality coefficient determines what fraction of per-capita wealth the **marginal worker** (bottom 40%) receives:

```
marginal_wealth = per_capita_wealth × (1 - inequality)
```

At `inequality=0.8`:
- Per-capita wealth = 0.10
- Marginal wealth = 0.10 × (1 - 0.8) = 0.02
- If consumption_needs = 0.05, marginal workers starve

## The Grinding Attrition Formula

The VitalitySystem now implements three phases instead of two:

### Phase 1: The Drain (Unchanged)
Linear subsistence burn based on class lifestyle:
```
cost = base_subsistence × subsistence_multiplier
wealth = max(0, wealth - cost)
```

### Phase 2: Grinding Attrition (NEW)
Probabilistic mortality based on inequality:

```python
# Step 1: Calculate per-capita and marginal wealth
effective_wealth_per_capita = wealth / population
marginal_wealth = effective_wealth_per_capita × (1 - inequality × inequality_impact)

# Step 2: Calculate mortality rate
if marginal_wealth >= consumption_needs:
    mortality_rate = 0
else:
    mortality_rate = (consumption_needs - marginal_wealth) / consumption_needs

# Step 3: Calculate deaths
deaths = floor(population × mortality_rate × base_mortality_factor)

# Step 4: Update population
population -= deaths
```

**Key insight**: Even with sufficient *average* wealth, high inequality means some workers lack access to that wealth and die.

### Phase 3: The Reaper (Extended)
Full extinction check:
- If `population = 0`: Mark `active = False`, emit `ENTITY_DEATH`
- If `population = 1` AND `wealth < consumption_needs`: Traditional binary death

## The Malthusian Correction

The formula creates natural equilibrium dynamics:

1. **Deaths occur** due to inequality → population decreases
2. **Per-capita wealth increases** (same wealth, fewer people)
3. **Marginal wealth increases** → fewer future deaths
4. **Population stabilizes** at carrying capacity

This models how populations historically adjusted to resource constraints through mortality, creating a "carrying capacity" based on available wealth.

**Example equilibrium**:
```
Tick 1: pop=1000, wealth=50, per_capita=0.05, marginal=0.01 → 10 deaths
Tick 2: pop=990,  wealth=50, per_capita=0.0505, marginal=0.0101 → 9 deaths
Tick 3: pop=981,  wealth=50, per_capita=0.051, marginal=0.0102 → 8 deaths
...
Tick N: equilibrium reached where marginal_wealth ≈ consumption_needs
```

## Events

### POPULATION_DEATH
Emitted when probabilistic deaths occur:
```python
{
    "entity_id": "C001",
    "deaths": 5,
    "remaining_population": 995,
    "mortality_rate": 0.005
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

```python
# In GameDefines.vitality
class VitalityDefines:
    base_mortality_factor: float = 0.01   # 1% of at-risk population dies per tick
    inequality_impact: float = 1.0        # Full inequality effect (can tune down)
```

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

## Theoretical Basis

The Mass Line refactor implements key Marxist concepts:

1. **Primitive Accumulation**: High inequality reflects dispossession
2. **Reserve Army of Labor**: Deaths create downward wage pressure
3. **Crisis of Social Reproduction**: Marginal workers can't reproduce themselves
4. **Metabolic Rift**: Ecological limits manifest through population dynamics

The name "Mass Line" references the Maoist principle of learning from the masses - the simulation now models demographic blocks rather than abstract individuals.

## Files Modified

| File | Change |
|------|--------|
| `src/babylon/models/types.py` | Added `Gini` constrained type [0,1] |
| `src/babylon/models/entities/social_class.py` | Added `population`, `inequality` fields |
| `src/babylon/config/defines.py` | Added `VitalityDefines` section |
| `src/babylon/models/enums.py` | Added `POPULATION_DEATH` event type |
| `src/babylon/engine/systems/vitality.py` | Implemented 3-phase vitality with Grinding Attrition |

## See Also

- **ADR033**: Mass Line Refactor decision record
- **demographics-spec.yaml**: Original demographics specification
- **metabolic-slice.yaml**: Ecological limits and carrying capacity
