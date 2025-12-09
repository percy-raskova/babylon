# Four-Phase Engine Blueprint

> **DEPRECATED:** Superseded by Six-Phase Fractal Evolution (2025-12-09). See `ai-docs/roadmap.md`.

**Status:** ~~Approved Roadmap~~ DEPRECATED
**Created:** 2024-12-07
**Principle:** Gall's Law - "A complex system that works is invariably found to have evolved from a simple system that worked."

## The Ambition vs The Reality

**Ambition:** Build something comparable to Dwarf Fortress or Victoria 3, but with MLM-TW internal logic.

**Reality:** If you try to build the "Whole World" at once, you will fail.

**Solution:** Four phases. Each phase produces a working system. Each phase is the foundation for the next.

---

## Phase 1: The Minimum Viable Dialectic (The Petri Dish)

### Goal
Build a simulation of **Two Nodes** connected by **One Edge**.

Not a map. Not the "World System." One relationship:

```
Core Factory Owner ←── value_flow ──→ Periphery Mine Worker
```

### The Task
Prove mathematically that:
1. Value flows from Worker to Owner (Imperial Rent)
2. Changing parameters (Police funding, wages) shifts Worker's Survival Probability P(S|R)

### Tech Stack
- Pure Python
- Pydantic for models
- Pytest for TDD
- **No UI. No AI.**

### Directory Structure
```
src/
├── mechanics/
│   ├── economics.py      # Unequal Exchange logic
│   └── topology.py       # Survival Manifold calculations
├── models/
│   └── agents.py         # Pydantic schemas for classes
└── main.py               # The simulation loop
```

### The Code

```python
# src/models/agents.py
from pydantic import BaseModel
from typing import Literal

class SocialClass(BaseModel):
    id: str
    role: Literal["core_bourgeoisie", "periphery_proletariat"]

    # Manifold Coordinates
    wealth: float = 10.0
    ideology: float = 0.0  # -1 (Revolutionary) to 1 (Reactionary)

    # Survival Calculus outputs
    p_acquiescence: float = 0.0
    p_revolution: float = 0.0

class Relationship(BaseModel):
    source_id: str
    target_id: str
    value_flow: float  # Imperial Rent (Φ)
    tension: float
```

### Day 1 Checklist
- [ ] Create `tests/unit/mechanics/test_exploitation.py`
- [ ] Write failing test: Periphery Worker cannot receive full value of labor
- [ ] Implement `src/mechanics/economics.py` to make it pass
- [ ] Assert: `owner.extracted_rent == worker.labor_value - worker.wage`

### Success Criteria
```python
def test_imperial_rent_extraction():
    worker = SocialClass(id="miner", role="periphery_proletariat")
    owner = SocialClass(id="factory", role="core_bourgeoisie")

    labor_value = 100
    wage_paid = 20

    rent = calculate_imperial_rent(labor_value, wage_paid)

    assert rent == 80  # Φ = W - V
    assert rent > 0    # Core always extracts from periphery
```

When this test passes, Phase 1 is complete.

---

## Phase 2: The Topological Engine (The Physics)

### Goal
Implement the "Action" logic. Classes move through phase space based on material conditions.

### The Task
Write the update loop that recalculates `SocialClass` coordinates based on `Relationship` flows.

### Components

#### 1. `mechanics/economics.py` - Value Flow
Implement Samir Amin / Unequal Exchange equations:
- Calculate `value_flow` based on wage differential
- Model how extraction affects wealth accumulation
- Track imperial rent over time

#### 2. `mechanics/topology.py` - Survival Calculus
```python
def calculate_survival_probabilities(
    wealth: float,
    subsistence: float,
    organization: float,
    repression: float
) -> tuple[float, float]:
    """
    Returns (p_acquiescence, p_revolution)

    P(S|A) = sigmoid(wealth - subsistence)
    P(S|R) = organization / repression
    """
    p_acquiescence = sigmoid(wealth - subsistence)
    p_revolution = organization / max(repression, 0.01)

    return p_acquiescence, p_revolution
```

### The TDD Script
Simulate 100 turns with assertions:

```python
def test_repression_triggers_revolution():
    state = create_initial_state()

    # Turn 0-49: High repression, worker is quiet
    for _ in range(50):
        state = advance_turn(state)
    assert state.worker.p_revolution < 0.3

    # Turn 50: Reduce repression dramatically
    state.repression = 0.1

    # Turn 51: Revolution probability spikes
    state = advance_turn(state)
    assert state.worker.p_revolution > 0.7

    # Turn 52+: Worker state changes
    state = advance_turn(state)
    assert state.worker.status == "INSURRECTION"
```

### Success Criteria
The text-based simulation runs 100 turns. Parameter changes cause predictable state transitions. **You have a game engine.**

---

## Phase 3: The Observer Pattern (The AI Integration)

### Goal
Give the simulation a voice. **AI watches, never controls.**

### Architecture
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Math Engine    │────▶│  Event Bus   │────▶│  AI Observer│
│  (Phase 1-2)    │     │  (Signals)   │     │  (Narrator) │
└─────────────────┘     └──────────────┘     └─────────────┘
        │                                            │
        │              ┌──────────────┐              │
        └─────────────▶│  State Object│◀─────────────┘
                       │  (Read Only) │   (AI reads, never writes)
                       └──────────────┘
```

### The Workflow

#### 1. Event Bus
Significant mathematical shifts emit signals:
```python
class GameEvent(BaseModel):
    type: str  # "REVOLUTION_PROBABILITY_CROSSED_THRESHOLD"
    data: dict
    turn: int

# When P(S|R) crosses 0.8:
emit(GameEvent(
    type="PERIPHERY_REVOLUTION_IMMINENT",
    data={"class": "miner", "p_revolution": 0.82},
    turn=51
))
```

#### 2. Context Builder
When signal fires, gather relevant data:
```python
context = {
    "class": "Periphery Mine Worker",
    "wage": 2.0,
    "labor_value": 10.0,
    "rent_extracted": 8.0,
    "repression_level": 0.1,
    "organization_level": 0.9
}
```

#### 3. RAG Lookup
Query ChromaDB for relevant theory/history:
- "Third World Debt Crisis"
- "Resource Curse"
- "Mineworker strikes historical"

#### 4. Narrative Generation
```python
narrative = generate_narrative(
    event=event,
    context=context,
    rag_results=rag_results
)
# "The miners of the Periphery, ground down by decades of
#  extraction, have begun to organize. With repression
#  weakening, the probability of uprising approaches critical..."
```

### Scalability
- AI is decoupled from math
- Can disable AI for fast testing
- Can swap models without breaking game logic
- Math tests don't require LLM

### Success Criteria
Events trigger appropriate narrative generation. Narrative reflects actual game state. AI never modifies state.

---

## Phase 4: The Control Room (The Dashboard)

### Goal
Visualize the Topology. Let players interact.

### Tech Stack
- NiceGUI for interface
- NetworkX for graph structure
- ECharts (via NiceGUI) for visualization

### Components

#### 1. The Graph View
```python
# Pass NetworkX graph to NiceGUI
G = nx.DiGraph()
G.add_node("owner", **owner.dict())
G.add_node("worker", **worker.dict())
G.add_edge("worker", "owner", value_flow=rent)

# Render with ECharts
ui.echart(graph_to_echart(G))
```

#### 2. The Phase Space
2D visualization:
- X-axis: Wealth
- Y-axis: Repression
- Moving dot: Current class position
- Shaded regions: Acquiescence zone, Revolution zone

#### 3. The Controls
Interactive sliders:
```python
ui.slider(min=0, max=1, value=0.5,
          on_change=lambda v: set_repression(v))
          .label("State Repression Budget")

ui.slider(min=0, max=1, value=0.5,
          on_change=lambda v: set_extraction(v))
          .label("Imperial Extraction Rate")
```

### Success Criteria
Player can:
1. See the current state visually
2. Adjust parameters with sliders
3. Watch the system evolve in real-time
4. Read AI-generated narrative for context

---

## Phase Summary

| Phase | Output | Dependencies | Duration |
|-------|--------|--------------|----------|
| 1 | Proven equations | None | Days |
| 2 | Working engine | Phase 1 | Week |
| 3 | Narrative layer | Phase 2 + ChromaDB | Week |
| 4 | Interactive UI | Phase 3 + NiceGUI | Week |

## The Mantra

> "Passing tests ship. Then game loops. Then players."

---

## Appendix: What NOT To Do

### Don't Start With
- ✗ The full map of America
- ✗ All 17 entity types
- ✗ The wiki engine
- ✗ AI narrative generation
- ✗ NiceGUI dashboard

### Do Start With
- ✓ Two nodes
- ✓ One edge
- ✓ One failing test
- ✓ Making it pass

---

## Relationship to Existing Work

### What We Keep
- `src/babylon/data/*.json` - Entity data (use later, Phase 4+)
- `src/babylon/schemas/` - Validation (use when scaling)
- `ai-docs/` - Context for development
- `brainstorm/` - Future features

### What We Build New
- `src/mechanics/` - The Phase 1-2 engine
- `src/engine/` - The game loop (after Phase 2)
- `src/narrative/` - The AI observer (Phase 3)
- `src/ui/` - The dashboard (Phase 4)

### What We Defer
- Gramscian wiki engine → After Phase 4
- Full faction system → After basic 2-node works
- 17 entity types → Scale up from 2 agents
