# Contract: LifecycleSystem

**Feature**: 030-dpd-lifecycle-circuit | **Date**: 2026-02-27

## System Identity

- **Name**: `LifecycleSystem`
- **Module**: `src/babylon/engine/systems/lifecycle.py`
- **Turn Order Position**: 7 (after CommunitySystem, before SolidaritySystem)
- **Protocol**: Implements `System` protocol (`name` property + `step(graph, services, context)`)

## Inputs

### Graph Node Data (per county)

| Key | Type | Source System | Required |
|-----|------|---------------|----------|
| `population` | `int` | Initial state / previous tick | Yes |
| `wealth` | `Currency` | EconomicSystem | Yes |
| `agitation` | `Probability` | ConsciousnessSystem (prev tick) | No (default 0.0) |
| `dpd_state` | `DPDState` | Previous tick's LifecycleSystem | No (initialized from defaults if absent) |
| `community_memberships` | `set[CommunityType]` | CommunitySystem | No |

### Services

| Service | Field | Usage |
|---------|-------|-------|
| `defines` | `services.defines.lifecycle` | All tunable parameters (LifecycleDefines) |
| `event_bus` | `services.event_bus` | Emit lifecycle events |

### Context

| Field | Usage |
|-------|-------|
| `context.tick` | Current simulation tick |
| `context.persistent_data` | Store previous tick's DPDState for conservation check |

## Outputs

### Graph Node Mutations (per county)

| Key | Type | Description |
|-----|------|-------------|
| `dpd_state` | `DPDState` | Updated population distribution and transition rates |
| `legitimation_state` | `LegitimationState` | Computed legitimation index and classification |
| `inheritance_flow` | `InheritanceFlow` | Wealth transfer at D' terminus (if deaths occurred) |
| `dependency_ratio` | `float` | (D + D') / P for downstream consumers |
| `legitimation_index` | `float` | Scalar for BifurcationRiskMetric integration |

### Events Emitted

| EventType | Condition | Payload |
|-----------|-----------|---------|
| `LIFECYCLE_TRANSITION` | Every tick (population moved) | `{fips, births, d_to_p, p_to_d_prime, deaths}` |
| `LEGITIMATION_CRISIS` | Classification changed to CRISIS | `{fips, index, prev_classification}` |
| `LEGITIMATION_RECOVERY` | Classification improved from CRISIS | `{fips, index, prev_classification}` |
| `INHERITANCE_TRANSFER` | D' deaths > 0 | `{fips, total, care_consumed, net, gini}` |
| `DUAL_CIRCUIT_INTERFERENCE` | Resource competition detected | `{fips, mechanism, severity}` |

## Processing Steps

```
step(graph, services, context):
    for each county node in graph:
        1. Read or initialize DPDState
        2. Compute births: births = birth_rate × pop_P
        3. Compute transitions:
           d_to_p = pop_D × rate_D_to_P
           p_to_d_prime = pop_P × rate_P_to_D_prime
           deaths = pop_D_prime × rate_D_prime_to_death
        4. Apply differential rates (racial/carceral modifiers)
        5. Update populations:
           new_pop_D = pop_D + births - d_to_p
           new_pop_P = pop_P + d_to_p - p_to_d_prime
           new_pop_D_prime = pop_D_prime + p_to_d_prime - deaths
        6. Verify conservation invariant (FR-002)
        7. Compute legitimation index (weighted blend)
        8. Classify legitimation state (CRISIS/UNSTABLE/STABLE)
        9. Compute inheritance flow (Pareto distribution of D' wealth)
        10. Compute ideology transmission (D→P phase, FR-009)
        11. Compute dual circuit metrics (FR-019–FR-023)
        12. Write updated state to graph node
        13. Emit events
```

## Invariants

1. **Population Conservation** (FR-002): Total population change equals births minus deaths, within 0.1% tolerance
2. **Non-negative Populations**: `pop_D >= 0`, `pop_P >= 0`, `pop_D_prime >= 0`
3. **Legitimation Bounds**: `0.0 <= legitimation_index <= 1.0`
4. **Inheritance Non-negative**: `net_inheritance >= 0` (care costs capped at available wealth)
5. **Gini Ordering**: `inheritance_gini >= income_gini` for same county (SC-003)
6. **Shadow Subsidy Positive**: Generational shadow subsidy > 0 for all classes (SC-014)

## Dependencies

### Upstream (must execute before LifecycleSystem)

| System | Provides |
|--------|----------|
| CommunitySystem | YOUTH/ADULT/ELDER hyperedge state, community memberships |
| EconomicSystem | County wealth data for inheritance calculation |
| ProductionSystem | Labor supply data |

### Downstream (executes after LifecycleSystem)

| System | Consumes |
|--------|----------|
| SolidaritySystem | Updated population distribution, dependency ratio |
| IdeologySystem | Ideology transmission from D→P transition |
| ContradictionSystem | Legitimation crisis events |
| BifurcationCalculator | `legitimation_index` via weighted blend |

## Error Handling

| Condition | Response |
|-----------|----------|
| Missing DPDState on node | Initialize from LifecycleDefines defaults |
| Conservation invariant violated > 0.1% | Log warning, normalize populations to conserve total |
| Negative population after transitions | Clamp to 0.0, log error, emit diagnostic event |
| Division by zero (pop_P = 0) | Set dependency_ratio to float('inf'), emit DUAL_CIRCUIT_INTERFERENCE |

## Performance Target

- `step()` completes in < 10ms per county per tick (FR-001)
- Operations are cohort arithmetic (array ops), not agent-level simulation
- No file I/O during step (II.6)
