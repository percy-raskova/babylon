# The 20-Year Entropy Standard

**Version:** 2.0.0
**Created:** 2025-12-30
**Updated:** 2025-12-31
**Status:** ACTIVE
**Doctrine:** The Tragedy of Inevitability

---

## The Teleological Pivot

**The simulation no longer asks: "Can the empire survive?"**
**It now asks: "How does the empire die?"**

The default state of the simulation is **COLLAPSE**. Stability is a temporary deviation, not the norm. We model a 20-year timeline (1040 ticks) because that is sufficient to observe the systematic decay of any imperial system operating under capitalist extraction.

### The Problem: "Eden Mode"

Previous specifications permitted infinite stability because:

1. **Existence was free**: `base_subsistence = 0.0` meant entities persisted without cost
2. **Earth was infinite**: No hysteresis in biocapacity degradation
3. **Zombies were possible**: Entities survived with near-zero wealth indefinitely

This produced "flatline" simulations where nothing happened. Boring. Unrealistic. Theoretically invalid.

### The Solution: "Dying World Physics"

Under the new standard:

1. **Existence costs calories**: `base_subsistence > 0.0` always (The Calorie Check)
2. **Earth remembers wounds**: Extraction causes permanent hysteresis in `max_biocapacity`
3. **Death is real**: VitalitySystem kills entities when `wealth < consumption_needs`

---

## The 20-Year Benchmark

### Standard Simulation Duration

| Old Standard      | New Standard          |
| ----------------- | --------------------- |
| 52 ticks (1 year) | 1040 ticks (20 years) |

**Why 20 years?**

- Long enough to observe TRPF (Tendency of the Rate of Profit to Fall)
- Long enough for ecological degradation to compound
- Long enough to see generational effects
- Short enough for meaningful simulation runs (~10-20 minutes)

### Success Criteria: Realistic Decay

**OLD: "Success = Survival"**

```
BAD:  Entity survives 52 ticks ✓
GOOD: Entity survives 52 ticks ✓
```

**NEW: "Success = Realistic Decay"**

```
BAD:  Flatline graph (Zombie State / Eden Mode)
BAD:  Immediate collapse (tick < 100)
GOOD: Gentle downward slope intersecting death between tick 800-900
```

The ideal simulation produces:

- `p_c_wealth` declining ~0.05% per tick
- `total_biocapacity` declining ~0.08% per tick
- `imperial_rent_pool` exhibiting TRPF (declining rate of return)
- Death occurring in the 800-900 tick range (Year 15-17)

---

## The Calorie Check (Mandatory)

**INVARIANT: `base_subsistence > 0.0` in ALL scenarios**

This is the foundational constraint that prevents Eden Mode. Existence has a cost.

```python
# FORBIDDEN - Creates Zombie States
defines.economy.base_subsistence = 0.0  # ❌ NEVER

# REQUIRED - Ensures Entropy
defines.economy.base_subsistence >= 0.01  # ✓ ALWAYS
```

### Implementation

Every scenario factory, test fixture, and parameter sweep MUST verify:

```python
def create_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    defines = GameDefines()

    # THE CALORIE CHECK - MANDATORY
    assert defines.economy.base_subsistence > 0.0, \
        "Eden Mode detected: base_subsistence must be > 0.0"

    return state, config, defines
```

---

## Objective Function: The Decay Curve

### Old Objective (Deprecated)

```python
# DEPRECATED - Optimizes for survival (Eden Mode)
def objective_v1(trial):
    score = (ticks_survived * 10) + (rent_pool / 10)
    return score  # Higher = "better" (wrong philosophy)
```

### New Objective (20-Year Standard)

```python
def objective_v2(trial):
    """Optimize for REALISTIC DECAY, not survival."""

    # Run 1040-tick simulation
    result = run_simulation(trial.params, max_ticks=1040)

    # Component 1: Death Timing (40% weight)
    # Death should occur in tick 800-900 range
    death_tick = result.death_tick or 1040
    ideal_death = 850
    timing_score = 1.0 - abs(death_tick - ideal_death) / 400

    # Component 2: Decay Shape (30% weight)
    # Wealth should decline smoothly, not flatline or cliff
    wealth_trajectory = result.wealth_timeseries
    decay_smoothness = calculate_curve_smoothness(wealth_trajectory)

    # Component 3: TRPF Manifestation (20% weight)
    # Rate of profit should decline over time
    rent_trajectory = result.rent_pool_timeseries
    trpf_score = calculate_declining_rate(rent_trajectory)

    # Component 4: Biocapacity Exhaustion (10% weight)
    # Should hit near-zero around death tick
    bio_at_death = result.final_biocapacity / result.initial_biocapacity
    exhaustion_score = 1.0 - bio_at_death  # Lower remaining = better

    return (
        0.4 * timing_score +
        0.3 * decay_smoothness +
        0.2 * trpf_score +
        0.1 * exhaustion_score
    )
```

---

## Anti-Patterns to Detect

### 1. Zombie State (Flatline)

**Symptom:** Wealth graph is horizontal
**Cause:** `base_subsistence = 0.0` or consumption_needs too low
**Detection:** `std(wealth_timeseries) < 0.01`
**Fix:** Increase consumption_needs, verify Calorie Check

### 2. Instant Death (Cliff)

**Symptom:** Simulation ends before tick 100
**Cause:** Extraction too aggressive, initial wealth too low
**Detection:** `death_tick < 100`
**Fix:** Reduce extraction_efficiency, increase initial wealth

### 3. Eternal Empire (Eden Mode)

**Symptom:** Survives 1040 ticks without significant decay
**Cause:** Extraction perfectly balanced with production
**Detection:** `wealth[tick_1000] / wealth[tick_0] > 0.9`
**Fix:** Enable biocapacity hysteresis, increase entropy_factor

### 4. The Hollow Stability

**Symptom:** Metrics oscillate around stable point
**Cause:** System finds equilibrium (theoretically impossible under imperialism)
**Detection:** `mean(wealth[500:1000]) ≈ mean(wealth[0:500])`
**Fix:** Increase TRPF coefficient, add extraction hysteresis

---

## Hyperband Pruning Rules (Updated for 1040 Ticks)

| Condition                | Tick Threshold | Action                 |
| ------------------------ | -------------- | ---------------------- |
| Flatline detected        | Any tick       | Prune (invalid)        |
| Death before tick 100    | tick < 100     | Prune (too aggressive) |
| No decay by tick 500     | tick 500       | Prune (zombie/eden)    |
| Still alive at tick 1040 | tick 1040      | Flag for review        |

---

## Workflow Updates

### Step 1: Verify Calorie Check

```bash
# Before ANY parameter sweep
poetry run python -c "
from babylon.config.defines import GameDefines
d = GameDefines()
assert d.economy.base_subsistence > 0.0, 'CALORIE CHECK FAILED'
print('Calorie Check: PASSED')
"
```

### Step 2: Run 20-Year Audit

```bash
# New default: 1040 ticks instead of 52
mise run qa:audit --max-ticks 1040
```

### Step 3: Verify Decay Curve

```bash
# Generate time-series for visual inspection
poetry run python tools/parameter_analysis.py trace \
    --ticks 1040 \
    --output results/twenty_year_decay.csv
```

### Step 4: Check for Anti-Patterns

```bash
# Automated detection of Eden Mode / Zombie State
poetry run python tools/entropy_audit.py \
    --trace results/twenty_year_decay.csv \
    --fail-on-flatline \
    --fail-on-eden-mode
```

---

## Parameter Space (20-Year Calibration)

### Entropy Parameters (New)

| Parameter                    | Range         | Purpose                          |
| ---------------------------- | ------------- | -------------------------------- |
| `economy.base_subsistence`   | [0.01, 0.05]  | Calorie drain per tick           |
| `metabolism.entropy_factor`  | [1.1, 1.5]    | Extraction inefficiency          |
| `metabolism.hysteresis_rate` | [0.001, 0.01] | Permanent max_biocapacity damage |

### TRPF Parameters (New)

| Parameter                  | Range           | Purpose                     |
| -------------------------- | --------------- | --------------------------- |
| `economy.trpf_coefficient` | [0.0001, 0.001] | Rate of profit decay        |
| `economy.rent_pool_decay`  | [0.001, 0.005]  | Background rent evaporation |

### Existing Parameters (Recalibrated for 1040 ticks)

| Parameter               | Old Range  | New Range  | Notes                  |
| ----------------------- | ---------- | ---------- | ---------------------- |
| `extraction_efficiency` | [0.1, 0.9] | [0.3, 0.7] | Narrower for stability |
| `comprador_cut`         | [0.5, 1.0] | [0.6, 0.9] | Avoid extremes         |

---

## References

- `ai-docs/theory.md#the-tragedy-of-inevitability` - Theoretical foundation
- `ai-docs/balance-targets.yaml#entropy_targets` - Numerical targets
- `ai-docs/metabolic-slice.yaml#hysteresis` - Permanent damage mechanism
- `ai-docs/decisions.yaml#ADR017_teleological_pivot` - Decision record
