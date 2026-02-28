# Contract: OODA Profile & Cycle Time

**Feature**: 032-ooda-loop-system
**Date**: 2026-02-28

## Purpose

Defines the OODAProfile data model and the cycle_time computation. The cycle time is the primary input to initiative scoring and determines how quickly an organization can act.

## Contract: OODAProfile Construction

### Type Definition

```python
class OODAProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    sensor_latency: int = Field(ge=0, le=10, default=1)
    ideological_coherence: float = Field(ge=0.0, le=1.0, default=0.5)
    analytical_capacity: float = Field(ge=0.0, le=1.0, default=0.5)
    decision_mode: DecisionMode = DecisionMode.DEMOCRATIC
    bureaucratic_depth: float = Field(ge=0.0, le=1.0, default=0.3)
    action_points: int = Field(ge=0, le=20, default=3)
    coordination_range: int = Field(ge=0, le=100, default=1)
    autonomy: float = Field(ge=0.0, le=1.0, default=0.5)
```

### Invariants

1. All fields are constrained to valid ranges at construction time (Pydantic validation).
2. OODAProfile is frozen — no mutation after construction.
3. Stored on organization graph nodes as `ooda_profile=profile.model_dump()`.

### Default Profiles by Org Type

| Org Type | sensor_latency | coherence | decision_mode | bureaucratic_depth | action_points | coord_range | autonomy |
|----------|---------------|-----------|---------------|-------------------|---------------|-------------|----------|
| StateApparatus (FBI) | 1 | 0.7 | AUTOCRATIC | 0.6 | 5 | 50 | 0.2 |
| StateApparatus (Local PD) | 2 | 0.4 | DELEGATE | 0.4 | 3 | 2 | 0.3 |
| PoliticalFaction (Vanguard) | 2 | 0.8 | AUTOCRATIC | 0.2 | 4 | 3 | 0.2 |
| PoliticalFaction (Mass) | 3 | 0.5 | DEMOCRATIC | 0.3 | 3 | 2 | 0.6 |
| CivilSocietyOrg | 2 | 0.3 | CONSENSUS | 0.2 | 2 | 1 | 0.7 |
| Business | 1 | 0.6 | AUTOCRATIC | 0.5 | 3 | 5 | 0.3 |

## Contract: Cycle Time Computation

### Function Signature

```
compute_cycle_time(profile: OODAProfile, defines: OODADefines) -> float
```

### Preconditions

1. `profile` is a valid OODAProfile instance.
2. `defines` provides all cycle time coefficients.

### Algorithm

```
Step 1: Observe phase duration
  observe_time = defines.base_observe_time + profile.sensor_latency * defines.latency_weight

Step 2: Orient phase duration
  orient_time = defines.base_orient_time * (1.0 - profile.ideological_coherence * defines.coherence_weight)
  orient_time = max(orient_time, 0.1)  # Floor: never zero

Step 3: Decide phase duration
  decision_base = defines.decision_mode_base[profile.decision_mode]
  decide_time = decision_base * (1.0 + profile.bureaucratic_depth * defines.depth_weight)

Step 4: Act phase duration
  act_time = defines.base_act_time  # Fixed base (coordination affects range, not speed)

Step 5: Total cycle time
  cycle_time = observe_time + orient_time + decide_time + act_time
```

### Postconditions

1. `cycle_time > 0` always (sum of positive terms).
2. AUTOCRATIC produces shorter cycle_time than DELEGATE < DEMOCRATIC < CONSENSUS (all else equal).
3. Higher ideological_coherence → shorter cycle_time (orient phase shorter).
4. Higher bureaucratic_depth → longer cycle_time (decide phase longer).
5. Higher sensor_latency → longer cycle_time (observe phase longer).

### Ordering Guarantee (FR-006)

For two profiles differing ONLY in decision_mode:
```
cycle_time(AUTOCRATIC) < cycle_time(DELEGATE) < cycle_time(DEMOCRATIC) < cycle_time(CONSENSUS)
```

This is guaranteed by decision_mode_base values: 1.0 < 2.0 < 3.0 < 5.0.

## Worked Example

**FBI (AUTOCRATIC, high coherence, moderate bureaucracy)**:
```
observe = 1.0 + 1 * 0.5 = 1.5
orient  = 2.0 * (1.0 - 0.7 * 0.6) = 2.0 * 0.58 = 1.16
decide  = 1.0 * (1.0 + 0.6 * 0.4) = 1.0 * 1.24 = 1.24
act     = 1.0
total   = 1.5 + 1.16 + 1.24 + 1.0 = 4.90
```

**Revolutionary Vanguard (AUTOCRATIC, high coherence, low bureaucracy)**:
```
observe = 1.0 + 2 * 0.5 = 2.0
orient  = 2.0 * (1.0 - 0.8 * 0.6) = 2.0 * 0.52 = 1.04
decide  = 1.0 * (1.0 + 0.2 * 0.4) = 1.0 * 1.08 = 1.08
act     = 1.0
total   = 2.0 + 1.04 + 1.08 + 1.0 = 5.12
```

**Mass Democratic Org (DEMOCRATIC, moderate coherence)**:
```
observe = 1.0 + 3 * 0.5 = 2.5
orient  = 2.0 * (1.0 - 0.5 * 0.6) = 2.0 * 0.70 = 1.40
decide  = 3.0 * (1.0 + 0.3 * 0.4) = 3.0 * 1.12 = 3.36
act     = 1.0
total   = 2.5 + 1.40 + 3.36 + 1.0 = 8.26
```

**Consensus CSO (CONSENSUS, low coherence)**:
```
observe = 1.0 + 2 * 0.5 = 2.0
orient  = 2.0 * (1.0 - 0.3 * 0.6) = 2.0 * 0.82 = 1.64
decide  = 5.0 * (1.0 + 0.2 * 0.4) = 5.0 * 1.08 = 5.40
act     = 1.0
total   = 2.0 + 1.64 + 5.40 + 1.0 = 10.04
```

Ordering: FBI (4.90) < Vanguard (5.12) < Mass Org (8.26) < CSO (10.04). AUTOCRATIC fastest, CONSENSUS slowest.
