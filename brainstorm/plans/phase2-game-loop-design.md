# Phase 2: The Game Loop Design

**Status:** Approved Design
**Phase:** 2
**Created:** 2024-12-07
**Core Insight:** Separate Data (State) from Logic (Systems). The State is what exists. The Engine is what transforms it.

---

## The Problem Phase 2 Solves

Phase 1 gave us:
- Static formulas that calculate things (imperial rent, survival probability, consciousness drift)
- Static entities (SocialClass, Relationship) that hold data
- 202 passing tests proving the math works

But nothing *moves*. The formulas exist, but nothing calls them repeatedly to simulate time passing.

**Phase 2 answers:** "What happens when outputs become the next turn's inputs?"

---

## The Core Architecture

### Data vs Logic Separation

| Layer | What It Is | Analogy |
|-------|-----------|---------|
| **WorldState** | Pure data snapshot | The chessboard position |
| **SimulationEngine** | Pure transformation logic | The rules of chess |

The State doesn't know *how* to change. The Engine doesn't know *what* the current values are.

This enables:
- **Determinism:** Same input always produces same output
- **Replayability:** Save initial conditions, replay entire history
- **Counterfactuals:** "What if repression was 0.3 instead of 0.6?"
- **Testability:** Feed state in, assert on state out

---

## WorldState: The Data Container

Think of WorldState as a **Matryoshka doll** - nested containers:

```
World
└── Country (USA)
    └── Region (Pacific Northwest)
        └── State (Oregon)
            └── City (Portland)
                └── Neighborhood (Alberta Arts District)
```

### The MLM-TW Tension

**Problem:** Settler-colonial boundaries are politically constructed, not natural. But the simulation needs *some* structure.

**Resolution:** The hierarchy is **administrative** (for storage), not **ontological** (claims about legitimacy).

**Key Insight:** Relationships can cross hierarchy levels. A neighborhood in Portland can have a direct economic relationship with a mining operation in Congo. The hierarchy is for *storage*. The graph edges are for *dynamics*.

### WorldState Components

```
WorldState
├── tick: int                    # Current turn number
├── date: datetime               # In-game calendar
├── entities: Dict[id, data]     # The nodes (social classes, etc.)
├── relationships: List[edges]   # The edges (value flows, tensions)
├── economy: EconomicState       # Material base snapshot
│   ├── gdp
│   ├── unemployment_rate
│   ├── gini_coefficient
│   ├── wage_share
│   ├── profit_rate
│   └── exploitation_rate
├── politics: PoliticalState     # Superstructure snapshot
│   ├── stability
│   ├── legitimacy
│   ├── repression_level
│   ├── class_consciousness
│   └── resistance_potential
└── event_logs: List[str]        # Recent events for narrative
```

---

## SimulationEngine: The Turn Processor

The Engine doesn't "decide" anything. It implements calculations and sets things in motion.

### What It Does Each Turn

```
Input State (tick N)
        │
        ▼
┌───────────────────────────────────┐
│  1. Economic Base Updates         │  ← Material conditions change first
│     - Calculate value flows       │
│     - Transfer imperial rent      │
│     - Update wealth levels        │
├───────────────────────────────────┤
│  2. Superstructure Reacts         │  ← Politics responds to economy
│     - Update stability            │
│     - Recalculate consciousness   │
│     - Adjust legitimacy           │
├───────────────────────────────────┤
│  3. Contradiction Evolution       │  ← Tensions calculated from both
│     - Update tension levels       │
│     - Check rupture (tension=1)   │
│     - Check synthesis (tension=0) │
├───────────────────────────────────┤
│  4. Event Processing              │  ← Threshold crossings fire events
│     - Log significant changes     │
│     - Record metrics              │
├───────────────────────────────────┤
│  5. State Capture                 │  ← Immutable snapshot for next tick
│     - Serialize new WorldState    │
└───────────────────────────────────┘
        │
        ▼
Output State (tick N+1)
```

### Order Encodes Theory

The order of operations **is** the theory:

> "Men must be in a position to live in order to be able to 'make history'." - Marx

Economy runs before Politics because **base determines superstructure**. If you wanted to model idealism (ideas drive history), you'd reverse the order. The architecture *encodes* historical materialism.

---

## The Feedback Loops

These are **implicit** in the order of operations, not explicitly coded as "feedback loops."

### Loop 1: The Rent Spiral

```
Economy extracts rent → Worker wealth drops
                              ↓
                   P(S|A) drops (can't survive through compliance)
                              ↓
                   P(S|A) < P(S|R) → Revolution becomes rational
                              ↓
                   Consciousness rises → Tension rises
                              ↓
                   (feeds into next tick)
```

### Loop 2: The Consciousness Decay

```
Worker gets raise → Wc/Vc > 1 (labor aristocracy)
                              ↓
                   Consciousness drifts reactionary
                              ↓
                   Organization drops → P(S|R) drops
                              ↓
                   Worker accepts system again
                              ↓
                   (feeds into next tick)
```

### Loop 3: The Repression Trap

```
State increases repression → P(S|R) drops short-term
                              ↓
                   Workers comply (P(S|A) > P(S|R))
                              ↓
                   BUT repression costs money → GDP drops
                              ↓
                   Owner cuts wages to pay for police
                              ↓
                   Worker wealth drops → Eventually P(S|A) < P(S|R)
                              ↓
                   Rupture delayed but INTENSIFIED
```

---

## Implementation Strategy

### Phase 2 Scope: Start Shallow

For Phase 2, we don't need the full Matryoshka:

```
Phase 2:
World
└── SocialClass (just two: Core Owner, Periphery Worker)

Phase 3+:
World
└── Country
    └── SocialClass (multiple per country)
```

The architecture **supports** arbitrary depth. The initial implementation is **shallow**. Gall's Law: get two nodes working before adding hierarchy.

### Abstract Base Pattern

Use a protocol or abstract base that allows expansion:

```python
class GeographicEntity(Protocol):
    id: str
    name: str
    parent_id: Optional[str]
    children_ids: List[str]

# Phase 2: Only SocialClass implements this
# Phase 3+: Country, Region, City also implement
```

### State Immutability

Treat WorldState as immutable:

```python
# Good: Function returns new state
new_state = advance_turn(old_state)

# Bad: Mutating state in place
state.advance()  # NO!
```

This enables:
- Diffing two states to see what changed
- Keeping history of all past states
- Branching for counterfactual analysis

---

## Success Criteria

When Phase 2 is complete:

1. **Scenario Setup:** "Worker starts with wealth=0.5, extraction=0.8, repression=0.6"

2. **Run Simulation:** Advance 100 turns

3. **Observe Deterministic Outcomes:**
   - Turn 23: Worker crosses poverty threshold
   - Turn 41: P(S|R) exceeds P(S|A)
   - Turn 67: Tension hits 1.0 - rupture

4. **Parameter Comparison:** Change repression to 0.3, run again, compare trajectories

### The Core Test

```python
def test_repression_triggers_revolution():
    state = create_initial_state()

    # Turn 0-49: High repression, worker quiet
    for _ in range(50):
        state = advance_turn(state)
    assert state.worker.p_revolution < 0.3

    # Turn 50: Reduce repression dramatically
    state.repression = 0.1

    # Turn 51: Revolution probability spikes
    state = advance_turn(state)
    assert state.worker.p_revolution > 0.7
```

---

## What Phase 2 Enables

The engine becomes a **laboratory for testing theory**:

| Question | How To Answer |
|----------|---------------|
| "Under what conditions is revolution inevitable?" | Sweep parameter space, find rupture boundaries |
| "What's the minimum extraction rate that sustains the system?" | Binary search on extraction parameter |
| "How long can repression delay rupture?" | Compare trajectories with different repression levels |

Not "what might happen" (narrative). Not "what should happen" (ideology).

**What does happen**, according to the mathematics.

---

## Relationship to Other Phases

| Phase | What It Does | Interface |
|-------|--------------|-----------|
| **1** | Prove equations (COMPLETE) | Tests only |
| **2** | Run equations forward in time | Text/logs |
| **3** | AI describes what happened | Narrative |
| **4** | Visual dashboard with sliders | Interactive UI |

Phase 2 is the **engine**. Phases 3 and 4 are ways to *observe* the engine.

---

## Gap Analysis (Pre-Implementation Review)

Before implementation, we identified 8 gaps that needed resolution:

### Critical Gaps (Resolved)

| # | Gap | Resolution |
|---|-----|------------|
| 1 | Entity-to-Aggregate relationship undefined | Aggregates computed from entities, not stored separately |
| 2 | Formula-to-Entity wiring missing | Explicit mapping spec in game-loop-architecture.yaml |
| 3 | **Economy/Politics don't use formulas.py** | **ADR010: Direct Entities + Formulas architecture** |

### Gap #3 Deep Dive: Disconnected Math Systems

**Discovery:** We found THREE independent mathematical systems:

```
formulas.py (40 tests)     Economy class (0 tests)     Politics class (0 tests)
├── calculate_imperial_rent    ├── _update_production        ├── _update_stability
├── calculate_consciousness    ├── _update_distribution      ├── _update_power_relations
├── calculate_acquiescence     ├── _update_class_relations   ├── _update_class_dynamics
└── (MLM-TW theory)            └── (generic simulation)      └── (generic simulation)
```

**Problem:** Economy/Politics use their own generic formulas, NOT the tested MLM-TW formulas.

**Decision (ADR010):** Bypass Economy/Politics classes entirely. SimulationEngine calls formulas.py directly on entities.

**Architecture:**
```
SimulationEngine.step()
    │
    ├── For each Relationship:
    │   └── calculate_imperial_rent() → update entity wealth
    │
    ├── For each SocialClass:
    │   ├── calculate_consciousness_drift() → update ideology
    │   ├── calculate_acquiescence_probability() → update p_acquiescence
    │   └── calculate_revolution_probability() → update p_revolution
    │
    └── For each Contradiction:
        └── ContradictionAnalysis.update_tension() → check rupture/synthesis
```

### Medium Gaps (Resolved)

| # | Gap | Resolution |
|---|-----|------------|
| 4 | Initialization strategy undefined | Factory function: `create_two_node_scenario()` |
| 5 | Phase transition effects undefined | ContradictionAnalysis handles; log + mark resolved |
| 6 | Coefficients location unclear | SimulationConfig Pydantic model |
| 8 | Feedback loop testing strategy | Property-based tests on trajectories |

### Low Priority Gaps (Deferred)

| # | Gap | Resolution |
|---|-----|------------|
| 7 | NetworkX integration unclear | Skip for Phase 2; use direct entity references |

---

## Formula-to-Entity Wiring Specification

Explicit mapping of formula parameters to entity fields:

### Imperial Rent Calculation
```
calculate_imperial_rent(alpha, periphery_wages, periphery_consciousness)
                          │           │                    │
                          │           │                    └── Worker.ideology (mapped to 0-1)
                          │           └── Worker.wealth / total_wealth
                          └── SimulationConfig.extraction_efficiency

Result → Relationship.value_flow
Effect → Worker.wealth -= rent, Owner.wealth += rent
```

### Consciousness Drift
```
calculate_consciousness_drift(core_wages, value_produced, current_consciousness, k, lambda)
                                  │             │                  │            │     │
                                  │             │                  │            │     └── CONSTANT 2.25
                                  │             │                  │            └── SimulationConfig.sensitivity
                                  │             │                  └── SocialClass.ideology
                                  │             └── Relationship.value_flow (what worker produces)
                                  └── SocialClass.wealth (what worker receives)

Result → delta_ideology
Effect → SocialClass.ideology += delta_ideology (clamped to [-1, 1])
```

### Survival Calculus
```
calculate_acquiescence_probability(wealth, subsistence_threshold, steepness_k)
                                      │              │                  │
                                      │              │                  └── SimulationConfig.survival_steepness
                                      │              └── SimulationConfig.subsistence_threshold
                                      └── SocialClass.wealth

Result → SocialClass.p_acquiescence

calculate_revolution_probability(cohesion, repression)
                                     │          │
                                     │          └── SimulationConfig.repression_level
                                     └── SocialClass.organization

Result → SocialClass.p_revolution
```

---

## Open Questions for Implementation

1. **Tick Duration:** What does one tick represent? One day? One month? One year?

2. **Event Granularity:** What state changes are significant enough to log?

3. **Initial Conditions:** How do we define the starting WorldState? JSON file? Factory function?

4. **Metrics:** What do we track for analysis? GDP over time? Tension curves?

---

## Files Created

- `ai-docs/game-loop-architecture.yaml` - Technical spec (machine-readable)
- `brainstorm/plans/phase2-game-loop-design.md` - This design document

---

## Next Steps (When Ready to Implement)

1. Write failing test: `test_advance_turn_updates_state()`
2. Create `WorldState` Pydantic model
3. Create `EconomicState` and `PoliticalState` component models
4. Create `SimulationEngine` class with `step()` method
5. Wire formulas into the turn order
6. Run 100 turns, verify feedback loops work
