> **STATUS: SUPERSEDED**
> **Current Spec:** `ai-docs/agency-layer.yaml`
> **Implemented In:** `src/babylon/engine/systems/struggle.py`
> **Archive Note:** This exploratory document is kept for historical context. The Agency Layer (George Floyd Dynamic) was implemented in Sprint 3.1.

---

# The Agency Layer: A Design Document

**Sprint: Agency Layer - The George Floyd Dynamic**

> "When it comes to the urban landscape, I think the burning of the buildings
> is as American as apple pie."
>
> — Kimberlé Crenshaw, on the 2020 Minneapolis Uprising

## 1. The Problem: Spectators of Their Own Oppression

### The Spectator Problem

In many political simulations, entities suffer material conditions but don't react.
Workers experience wage cuts, face police violence, and watch their wealth extracted —
but they remain passive observers. The simulation models what happens *to* them,
not what they *do*.

This creates a fundamental failure in modeling historical materialism. In the real
world, oppression generates resistance. State violence creates political moments.
Material deprivation builds revolutionary potential.

### The Missing Mechanic

The existing Babylon engine modeled:
- **Imperial Rent**: Value extraction from periphery to core
- **Consciousness Drift**: Ideology changes based on material conditions
- **Survival Calculus**: P(S|A) vs P(S|R) probability comparisons
- **Bifurcation**: Agitation routing to class or national consciousness

What was missing: **Agency**. The ability of oppressed classes to *act* on their
conditions and thereby *change* the material substrate of the simulation.

## 2. The Theory: The George Floyd Dynamic

### Historical Precedent

On May 25, 2020, Minneapolis police murdered George Floyd. Within days, protests
erupted across all 50 states and dozens of countries. The Minneapolis Third Precinct
was burned. The National Guard was deployed. For a moment, the question of revolution
was on the American agenda.

Why then? Police killings happen constantly. The answer lies in the conjunction of:

1. **The Spark**: A visible, documented act of state violence (Floyd's murder)
2. **The Fuel**: Accumulated grievances (COVID unemployment, economic anxiety, accumulated police violence)
3. **The Combustion**: Conditions where acquiescence offers no safety (pandemic = everyone vulnerable)

### The Formula

```
State Violence (The Spark) + Accumulated Agitation (The Fuel) = Insurrection (The Explosion)
```

But the *outcome* of the explosion depends on pre-existing organizational infrastructure.
Minneapolis had Black Lives Matter networks. Portland had antifascist organizing.
The uprising could coordinate, communicate, and sustain itself.

In atomized communities without solidarity infrastructure, the same spark produces
isolated incidents that the state easily suppresses. The energy dissipates into
individual acts of desperation rather than collective revolutionary action.

### The Strategic Insight

**Revolution is built through shared struggle, not spontaneous awakening.**

The explosion is what builds the solidarity bridges. People who face tear gas together
develop bonds. Mutual aid networks form during crises. The organizational infrastructure
that enables consciousness transmission is *constructed* through collective action.

This inverts the typical model where consciousness precedes action. In reality:

```
Material Crisis → Spontaneous Resistance → Shared Struggle → Solidarity Infrastructure
→ Consciousness Transmission → Organized Revolutionary Movement
```

## 3. The Implementation: The Struggle System

### System Overview

The `StruggleSystem` runs after `SurvivalSystem` (needs P values) and before
`ContradictionSystem`. It processes entities with `PERIPHERY_PROLETARIAT` and
`LUMPENPROLETARIAT` roles — the classes facing the highest repression.

### The Algorithm

```
For each eligible entity:

1. SPARK GENERATION
   spark_probability = repression_faced × spark_probability_scale
   Roll random()
   If hit → Emit EXCESSIVE_FORCE event

2. UPRISING CHECK
   uprising_condition = (spark_occurred OR (P(S|R) > P(S|A)))
                        AND (agitation > resistance_threshold)

3. IF UPRISING:
   a. Economic Damage
      wealth *= (1 - wealth_destruction_rate)

   b. Solidarity Infrastructure
      For each incoming SOLIDARITY edge:
          solidarity_strength += solidarity_gain_per_uprising

   c. Consciousness Boost
      class_consciousness += solidarity_gain × 0.5

   d. Emit UPRISING and SOLIDARITY_SPIKE events
```

### Event Types

| Event | Description | Trigger |
|-------|-------------|---------|
| `EXCESSIVE_FORCE` | The Spark | Random roll under (repression × spark_scale) |
| `UPRISING` | The Explosion | Spark/pressure + agitation > threshold |
| `SOLIDARITY_SPIKE` | The Bridge Building | Uprising with existing solidarity edges |

### Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `spark_probability_scale` | 0.1 | Multiplier for EXCESSIVE_FORCE probability |
| `resistance_threshold` | 0.1 | Minimum agitation for uprising |
| `wealth_destruction_rate` | 0.05 | Fraction of wealth destroyed per uprising |
| `solidarity_gain_per_uprising` | 0.2 | Solidarity strength added per uprising |

## 4. Game Loop Integration

### Updated System Order

```
SimulationEngine.run_tick()
    │
    ├── 1. ImperialRentSystem      → Modifies wealth/wages (economic base)
    ├── 2. SolidaritySystem        → Transmits consciousness via SOLIDARITY edges
    ├── 3. ConsciousnessSystem     → Routes agitation (bifurcation mechanic)
    ├── 4. SurvivalSystem          → Calculates P(S|A), P(S|R)
    ├── 5. StruggleSystem          → AGENCY: sparks, uprisings, solidarity building  ← NEW
    ├── 6. ContradictionSystem     → Tension/rupture dynamics
    └── 7. TerritorySystem         → Spatial mechanics
```

### Data Flow Diagram

```
                    ┌─────────────────────────────┐
                    │      SurvivalSystem         │
                    │   (P(S|A), P(S|R) calc)     │
                    └─────────────┬───────────────┘
                                  │ p_acquiescence, p_revolution
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           StruggleSystem                                     │
│                                                                              │
│  Inputs:                          Outputs:                                   │
│  ├─ repression_faced              ├─ EXCESSIVE_FORCE events                 │
│  ├─ agitation                     ├─ UPRISING events                         │
│  ├─ p_acquiescence                ├─ SOLIDARITY_SPIKE events                 │
│  ├─ p_revolution                  ├─ Modified wealth                         │
│  └─ SOLIDARITY edges              ├─ Modified class_consciousness            │
│                                   └─ Modified solidarity_strength            │
│                                                                              │
│  Algorithm:                                                                  │
│  1. Roll for EXCESSIVE_FORCE (spark)                                        │
│  2. Check uprising condition (spark/pressure + agitation)                    │
│  3. Execute uprising (damage + solidarity + consciousness)                   │
│                                                                              │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │ solidarity_strength (for next tick)
                              ▼
                    ┌─────────────────────────────┐
                    │    ContradictionSystem      │
                    │   (tension dynamics)        │
                    └─────────────────────────────┘
```

## 5. Emergent Dynamics

### The Revolutionary Spiral (Virtuous Cycle)

When conditions are right, the system produces a self-reinforcing revolutionary dynamic:

```
High Repression
      │
      ▼
EXCESSIVE_FORCE (Sparks)
      │
      ▼
UPRISING (if agitated)
      │
      ├──► Wealth Destruction (cost)
      │
      └──► Solidarity Gain (benefit)
              │
              ▼
        Consciousness Transmission
        (via SolidaritySystem next tick)
              │
              ▼
        Higher P(S|R)
              │
              ▼
        More Uprisings Likely
              │
              └──► Return to top
```

**Conditions for Activation:**
- High `repression_faced` (> 0.5)
- Existing `agitation` (> resistance_threshold)
- Existing `SOLIDARITY` edges (for infrastructure building)

### The Atomization Trap (Vicious Cycle)

Without pre-existing solidarity infrastructure, the system cannot build revolutionary
momentum:

```
High Repression
      │
      ▼
EXCESSIVE_FORCE (Sparks)
      │
      ▼
UPRISING (isolated)
      │
      ├──► Wealth Destruction (cost)
      │
      └──► NO Solidarity Gain (no edges exist!)
              │
              ▼
        Agitation Routes to National Identity
        (via ConsciousnessSystem bifurcation)
              │
              ▼
        Fascism, Not Revolution
```

This connects directly to the Fascist Bifurcation mechanic:
- **StruggleSystem** builds solidarity infrastructure through shared struggle
- **ConsciousnessSystem** routes agitation based on solidarity_pressure
- Without StruggleSystem, solidarity edges stay at 0.0
- With solidarity=0.0, agitation routes to fascism, not revolution

### The Strategic Implication for Players

The player's task is to build the organizational infrastructure *before* crisis hits.
Once the spark occurs, it's too late to start organizing. The outcome is determined
by the solidarity edges that already exist.

This models the real strategic dilemma of revolutionary organizing:
- Building infrastructure during stable periods feels pointless (no visible crisis)
- But infrastructure built during crisis is too late
- The dialectic of preparation vs. spontaneity

## 6. Connection to MLM-TW Theory

### The Role of the Vanguard

In Marxist-Leninist theory, the vanguard party's role is to build organizational
infrastructure during stable periods so that when crisis hits, the working class
has the capacity to respond coherently.

The StruggleSystem models this by making solidarity edge strength a *prerequisite*
for effective uprising. Spontaneous rebellion without organization produces:
- Economic damage (wealth destruction)
- BUT NOT lasting organizational gains (no solidarity increase without edges)

### The Third World Question

The system targets `PERIPHERY_PROLETARIAT` and `LUMPENPROLETARIAT` because in MLM-TW
theory, the Third World proletariat has the highest revolutionary potential:
- Highest repression_faced (colonialism, police states)
- Lowest P(S|A) (poverty means acquiescence doesn't ensure survival)
- Highest agitation (material deprivation)

The First World labor aristocracy typically has:
- Low repression_faced (civil liberties, welfare state)
- High P(S|A) (material comfort makes acquiescence rational)
- Low agitation (super-wages buy off discontent)

This explains why the StruggleSystem excludes `LABOR_ARISTOCRACY` and `CORE_BOURGEOISIE`
from eligibility — their material conditions rarely produce the desperation required
for uprising.

## 7. Code Locations

| Component | File |
|-----------|------|
| `StruggleSystem` class | `src/babylon/engine/systems/struggle.py` |
| `StruggleDefines` parameters | `src/babylon/config/defines.py` |
| YAML configuration | `src/babylon/data/defines.yaml` |
| Event types | `src/babylon/models/enums.py` |
| Integration tests | `tests/integration/test_george_floyd_dynamic.py` |
| AI documentation | `ai-docs/agency-layer.yaml` |

---

*Document created for the Agency Layer Sprint - The George Floyd Dynamic*
*December 2025*
