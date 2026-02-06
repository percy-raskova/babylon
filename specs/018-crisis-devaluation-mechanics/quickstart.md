# Quickstart: Crisis and Devaluation Mechanics (Feature 018)

**Date**: 2026-02-06
**Feature**: 018-crisis-devaluation-mechanics

## What This Feature Does

Feature 018 replaces the binary crisis detection (`ThresholdCrisisDetector`) with a multi-period crisis lifecycle system. It tracks the tendency of the rate of profit to fall (TRPF) across consecutive periods, triggers phased dispossession cascades, computes a George Jackson bifurcation risk metric, and models wage compression feedback loops during deep crisis.

## Key Concepts

### Multi-Period Crisis Detection

The existing `ThresholdCrisisDetector` checks single-period unemployment and profit decline. This feature replaces it with `MultiPeriodCrisisDetector` that:

- Uses the flow-based profit rate `s/(c+v)` from `ValueTensor4x3` (not the stock-based rate)
- Requires N consecutive periods below `r_threshold` before declaring crisis
- Removes unemployment as a crisis trigger (unemployment is a symptom, not a cause)
- Evaluates quarterly (every 13 ticks) via batch-within-step design in the annual pipeline

### Crisis Phase Lifecycle

Crisis is no longer boolean. Counties progress through five phases:

```
NORMAL → ONSET → EARLY → DEEP → RECOVERY → NORMAL
```

Each phase has distinct amplification multipliers for class transition rates. Deeper crisis accelerates downward transitions (dispossession, precaritization) while suppressing upward mobility (accumulation, stabilization).

### Bifurcation Risk

During active crisis, a bifurcation risk metric (`[-1, +1]`) indicates whether the population trends toward revolutionary solidarity (-1) or fascist reaction (+1). This is the George Jackson Bifurcation: identical material crises produce opposite political outcomes depending on solidarity topology.

### Wage Compression (Crisis Trap)

In deep crisis, wages compress by 2% per period. When wages fall below the subsistence floor, accumulation halts entirely, creating a self-sustaining crisis equilibrium.

## Module Location

```
src/babylon/economics/tick/
    crisis_detector.py    # MultiPeriodCrisisDetector (REPLACES ThresholdCrisisDetector)
    types.py              # CrisisState, CrisisPhase, BifurcationRiskMetric (ADDED)
    system.py             # Step 5 + Step 6 modifications
    graph_bridge.py       # Updated for CrisisState serialization

src/babylon/economics/dynamics/
    crisis.py             # PhasedCrisisAmplifier (REPLACES DefaultCrisisAmplifier)
    data_sources.py       # CrisisAmplifier protocol (UNCHANGED, backward compat)

src/babylon/economics/crisis/
    bifurcation.py        # BifurcationRiskCalculator (NEW)

src/babylon/config/defines.py  # CrisisDefines category (NEW)

src/babylon/models/enums.py    # EventType extensions (MODIFIED)

tests/unit/economics/tick/
    test_multi_period_detector.py  # MultiPeriodCrisisDetector tests (NEW)
    test_crisis.py                 # Updated for new detector

tests/unit/economics/dynamics/
    test_phased_amplifier.py       # PhasedCrisisAmplifier tests (NEW)
    test_crisis.py                 # Updated for phased amplification

tests/unit/economics/crisis/
    test_bifurcation_risk.py       # BifurcationRiskCalculator tests (NEW)
    test_crisis_lifecycle.py       # Full lifecycle integration (NEW)
    test_wage_compression.py       # Wage compression + crisis trap (NEW)
```

## Usage Pattern

### Crisis Detection (Step 5)

```python
from babylon.economics.tick.crisis_detector import MultiPeriodCrisisDetector
from babylon.economics.tick.types import CrisisState

detector = MultiPeriodCrisisDetector(
    r_threshold=0.05,
    n_consecutive=3,
    m_recovery=2,
    r_cap=8,
)

# Evaluate one quarter (called 4x per annual pipeline run)
new_state = detector.evaluate(
    profit_rate=0.04,         # From ValueTensor4x3.profit_rate
    current_state=county.crisis_state,
)
# new_state.phase may have advanced (e.g., NORMAL -> accumulating -> ONSET)
```

### Phased Amplification (Step 6)

```python
from babylon.economics.dynamics.crisis import PhasedCrisisAmplifier
from babylon.economics.tick.types import CrisisPhase

amplifier = PhasedCrisisAmplifier(profiles=crisis_defines.profiles)

# Phase-aware amplification
amplified = amplifier.amplify_phased(
    rates=base_transition_rates,
    phase=county.crisis_state.phase,
)

# Backward-compatible boolean interface (maps True -> DEEP)
amplified = amplifier.amplify(rates=base_transition_rates, crisis=True)
```

### Bifurcation Risk Computation

```python
from babylon.economics.crisis.bifurcation import BifurcationRiskCalculator

calculator = BifurcationRiskCalculator(
    solidarity_weight=1.0,
    burden_weight=1.0,
    epsilon=0.001,
)

metric = calculator.compute(
    graph=graph,
    fips="26163",
    crisis_state=county.crisis_state,
    previous_distribution=prev_dist,
    current_distribution=curr_dist,
)
# metric.score: -0.4 (leaning revolutionary)
```

### Access Crisis Data from Graph (Downstream Systems)

```python
# In another System's step() method:
def step(self, graph, services, context):
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") != "territory":
            continue
        crisis_phase = data.get("tick_crisis_phase", "NORMAL")
        bifurcation = data.get("tick_bifurcation_score", 0.0)
        wage_compression = data.get("tick_wage_compression", 0.0)
```

## Dependencies

Feature 018 extends the existing economics pipeline:

| Feature | What It Provides | Used For |
|---------|-----------------|----------|
| 011 | ValueTensor4x3 | Flow-based profit rate `s/(c+v)` |
| 016 | CrisisAmplifier protocol, TransitionRates | Backward-compatible amplification |
| 017 | TickDynamicsSystem pipeline, CountyEconomicState | Pipeline integration, state storage |
| Engine | EventBus, EventType, SOLIDARITY edges | Crisis events, bifurcation inputs |

## Testing

```bash
# Unit tests for crisis detection
poetry run pytest tests/unit/economics/tick/test_multi_period_detector.py -v

# Unit tests for phased amplification
poetry run pytest tests/unit/economics/dynamics/test_phased_amplifier.py -v

# Unit tests for bifurcation risk
poetry run pytest tests/unit/economics/crisis/test_bifurcation_risk.py -v

# Full lifecycle integration tests
poetry run pytest tests/unit/economics/crisis/test_crisis_lifecycle.py -v

# All crisis-related tests
poetry run pytest tests/ -k "crisis" -v
```

## Configuration

All crisis parameters are in `GameDefines.crisis`:

```python
from babylon.config.defines import GameDefines

defines = GameDefines()
defines.crisis.r_threshold          # 0.05 (5%)
defines.crisis.n_consecutive        # 3 periods
defines.crisis.crisis_period_ticks  # 13 ticks (quarterly)
defines.crisis.hysteresis_coefficient  # 0.5
defines.crisis.wage_compression_rate   # 0.02 (2% per period)
```
