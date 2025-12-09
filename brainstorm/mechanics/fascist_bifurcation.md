# The Fascist Bifurcation: A Design Document

**Sprint 3.4.3 - The George Jackson Refactor**

> "Fascism is the last defense of capitalism. It is called into being when the traditional
> means of suppression fail to contain the masses."
>
> — George Jackson, *Blood in My Eye* (1972)

## 1. The Theoretical Core

### The Jackson Insight

Traditional political models place "Left" and "Right" on a single axis, implying that Fascism
is merely the opposite of Communism. This is a fundamental category error.

George Jackson understood that **Fascism is not a political position but a defensive reflex**.
When capitalism enters crisis, the ruling class has two options:

1. **Reform**: Redistribute wealth to placate workers (Social Democracy)
2. **Reaction**: Redirect worker anger toward scapegoats (Fascism)

Option 1 requires material sacrifice from the bourgeoisie. Option 2 preserves their position
by fragmenting working-class unity. The choice depends entirely on the **material conditions**
and the **organizational capacity** of the working class.

### Why Conservatism Becomes Fascism

"Conservatism" (maintenance of the status quo) is stable only during periods of **material
abundance**. When wages fall, workers face a survival crisis. Their political energy must
go somewhere.

- **With Solidarity**: Crisis energy channels into **class consciousness** — workers
  recognize their shared material interests against capital.
- **Without Solidarity**: Crisis energy channels into **national identity** — workers
  blame other workers (immigrants, minorities) rather than the system.

This is the **Fascist Bifurcation**: the same material crisis produces opposite political
outcomes depending on the presence of working-class solidarity.

## 2. The Topology: The Ideological Compass

### The 2D Phase Space

The legacy model used a single scalar `ideology` in range [-1, +1]:
- `-1` = Revolutionary
- `+1` = Reactionary

This was replaced in Sprint 3.4.3 with a **multi-dimensional `IdeologicalProfile`**:

```
                    class_consciousness
                           (Y)
                            ^
                            |
              REVOLUTIONARY |
                (1.0, 0.0) *|
                            |
                            |
                            |
    INTERNATIONALIST -------+--------> FASCIST
         (0.0)              |          (1.0)
                            |     national_identity (X)
                            |
                            |
         FALSE CONSCIOUSNESS|
                (0.0, 0.5) *|
                            |
                            v
```

### Axis Definitions

| Axis | Range | Meaning |
|------|-------|---------|
| **Y: Class Consciousness** | [0.0, 1.0] | Relationship to Capital: 0=False Consciousness, 1=Revolutionary |
| **X: National Identity** | [0.0, 1.0] | Relationship to State/Tribe: 0=Internationalist, 1=Nativist/Fascist |

### Key Coordinates

| Position | (class_consciousness, national_identity) | Description |
|----------|------------------------------------------|-------------|
| **Status Quo** | (0.0, 0.5) | Default starting point. Low class awareness, moderate national feeling. |
| **Revolutionary** | (1.0, 0.0) | Full class consciousness, internationalist solidarity. |
| **Fascist** | (0.0, 1.0) | No class consciousness, maximum nativist identification. |
| **Social Democrat** | (0.5, 0.3) | Moderate class awareness, some national feeling. |

### The Third Dimension: Agitation

`agitation` is not a position but **energy** — accumulated political charge from material crisis:

- **Source**: Falling wages (`wage_change < 0`)
- **Range**: [0.0, +inf)
- **Behavior**: Accumulated, then routed to either X or Y axis based on solidarity

## 3. The Mechanic: The Agitation Router

### Input: Crisis Detection

The system detects crisis by tracking wage changes between simulation ticks:

```python
wage_change = current_wages - previous_wages
```

Only **negative** wage changes generate agitation. Rising wages = stability.

### Energy Generation

When wages fall, agitation energy is generated using the **Loss Aversion Coefficient** (λ = 2.25):

$$E = |\Delta W| \times \lambda$$

Where:
- $E$ = Agitation energy generated
- $\Delta W$ = Wage change (negative)
- $\lambda$ = 2.25 (from behavioral economics: losses hurt ~2.25x more than equivalent gains)

### The Switch: Solidarity Routing

The accumulated agitation routes to the ideological axes based on `solidarity_pressure`:

```
solidarity_factor = min(1.0, solidarity_pressure)

class_delta   = agitation × solidarity_factor × 0.1
nation_delta  = agitation × (1.0 - solidarity_factor) × 0.1
```

**The Key Insight**:
- `solidarity_pressure > 0`: Energy flows to **class_consciousness** (Y-axis)
- `solidarity_pressure = 0`: Energy flows to **national_identity** (X-axis)

### Solidarity Pressure Calculation

`solidarity_pressure` is computed by summing incoming `SOLIDARITY` edge strengths
from neighbors with revolutionary consciousness:

```python
for edge in incoming_SOLIDARITY_edges:
    if source.class_consciousness > activation_threshold:
        solidarity_pressure += edge.solidarity_strength
```

The `activation_threshold` (default 0.3) ensures only meaningfully class-conscious
neighbors contribute to solidarity pressure.

### Agitation Decay

Agitation decays over time (default 10% per tick):

```python
new_agitation = agitation × (1.0 - agitation_decay)
```

This models how political energy dissipates without sustained crisis.

## 4. Game Loop Integration

### System Execution Order

The bifurcation mechanic integrates into the simulation engine as part of `ConsciousnessSystem`:

```
SimulationEngine.run_tick()
    │
    ├── 1. ImperialRentSystem   → Modifies wealth/wages
    ├── 2. SolidaritySystem     → Updates SOLIDARITY edge strengths
    ├── 3. ConsciousnessSystem  → Detects crisis, routes agitation  ← HERE
    ├── 4. SurvivalSystem       → Calculates P(S|A), P(S|R)
    ├── 5. ContradictionSystem  → Tension/rupture dynamics
    └── 6. TerritorySystem      → Spatial mechanics
```

### Data Flow

```
                    ┌─────────────────────────────┐
                    │    ImperialRentSystem       │
                    │  (wealth extraction)        │
                    └─────────────┬───────────────┘
                                  │ wage_flow via WAGES edges
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    SolidaritySystem                         │
│  (transmits class_consciousness through SOLIDARITY edges)   │
└─────────────────────────────┬───────────────────────────────┘
                              │ solidarity_strength edges
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ConsciousnessSystem                       │
│                                                             │
│  1. Calculate wage_change from previous tick                │
│  2. Sum incoming SOLIDARITY strengths → solidarity_pressure │
│  3. If wage_change < 0:                                     │
│        agitation += |wage_change| × λ                       │
│  4. Route agitation:                                        │
│        class_consciousness += agitation × solidarity × 0.1  │
│        national_identity += agitation × (1-solidarity) × 0.1│
│  5. Decay agitation                                         │
│                                                             │
└─────────────────────────────┬───────────────────────────────┘
                              │ updated IdeologicalProfile
                              ▼
                    ┌─────────────────────────────┐
                    │    SurvivalSystem           │
                    │  (rupture probability)      │
                    └─────────────────────────────┘
```

### Code Locations

| Component | File | Line |
|-----------|------|------|
| `IdeologicalProfile` model | `src/babylon/models/entities/social_class.py` | 36-128 |
| `ConsciousnessSystem` | `src/babylon/engine/systems/ideology.py` | 62-156 |
| `calculate_ideological_routing()` | `src/babylon/systems/formulas.py` | 442-522 |
| `LOSS_AVERSION_COEFFICIENT` | `src/babylon/systems/formulas.py` | 28 |

## 5. Emergent Dynamics

### Path to Fascism

1. **Crisis**: Imperial rent extraction causes wages to fall
2. **Atomization**: No SOLIDARITY edges exist (workers isolated)
3. **Agitation**: Energy accumulates from material loss
4. **Routing**: Energy flows to national_identity axis
5. **Outcome**: Workers blame immigrants, minorities — not capital

### Path to Revolution

1. **Crisis**: Same wage fall from imperial extraction
2. **Organization**: Workers have built SOLIDARITY edges
3. **Agitation**: Same energy accumulates
4. **Routing**: Energy flows to class_consciousness axis
5. **Outcome**: Workers recognize shared class interest, organize against capital

### The Strategic Implication

This mechanic models why **labor organizing** is the decisive variable in crisis outcomes.
Material crisis alone does not determine the political result — the **organizational
infrastructure** present when crisis hits determines whether fascism or revolution emerges.

## 6. Legacy Compatibility

The `IdeologicalProfile` class provides conversion methods for systems still using
scalar ideology:

```python
# Convert legacy scalar [-1, +1] to IdeologicalProfile
profile = IdeologicalProfile.from_legacy_ideology(-0.5)

# Convert IdeologicalProfile back to legacy scalar
scalar = profile.to_legacy_ideology()
```

**Legacy Mapping**:
- `ideology = -1` (revolutionary) → `class_consciousness=1.0, national_identity=0.0`
- `ideology = 0` (neutral) → `class_consciousness=0.5, national_identity=0.5`
- `ideology = +1` (reactionary) → `class_consciousness=0.0, national_identity=1.0`

---

*Document created for Sprint 3.4.3 - The George Jackson Refactor*
*December 2025*
