# The Six-Phase Fractal Evolution

**Principle:** The simulation is built like a civilization: Base first, then Superstructure.

> "The mode of production of material life conditions the general process of social,
> political and intellectual life. It is not the consciousness of men that determines
> their existence, but their social existence that determines their consciousness."
>
> — Karl Marx, *A Contribution to the Critique of Political Economy* (1859)

---

## Phase I: The Kernel (Logic)

**Focus:** Pure Math.

**Deliverables:**
- `formulas.py` - 12 MLM-TW formulas (imperial rent, survival calculus, unequal exchange)
- Pydantic Models - Constrained types (Probability, Currency, Ideology)
- Unit tests proving the equations work in isolation

**Status:** COMPLETE

**Key Insight:** Before you can model history, you must model the laws of motion.

---

## Phase II: The Mesh (Topology)

**Focus:** Graph Theory.

**Deliverables:**
- `WorldState` - Immutable state with NetworkX graph conversion
- Systems Architecture - Modular engine with dependency injection
- Feedback loops - Rent spiral, consciousness drift, repression trap

**Status:** COMPLETE

**Key Insight:** "Graph + Math = History" - The topology encodes relationships,
the formulas encode dynamics.

---

## Phase III: The Material Base (Physics)

**Focus:** The "Body" of the world.

**Components:**

### Layer 0: Territory, Heat, Eviction (Sprint 3.5)
- Strategic Sectors - territorial units with operational profiles
- Subversive Tenancy - De Facto vs Legal control
- Heat mechanics - state attention accumulation
- Eviction pipeline - when heat >= 0.8

**Status:** COMPLETE

### Layer 1: Imperial Circuit, Rent, Wages (Sprint 3.4)
- WAGES edge - super-wages from bourgeoisie to core workers
- TRIBUTE edge - imperial rent transfer
- CLIENT_STATE edge - imperial subsidy to comprador
- 4-node model - periphery worker, comprador, core bourgeoisie, core worker

**Status:** IN PROGRESS (Sprints 3.4.1-3.4.3 COMPLETE, 3.4.4 remaining)

**Goal:** A physically consistent world where material conditions drive events.

**Key Insight:** "The bomb factory pays well. That's the problem."

---

## Phase IV: The Superstructure (Semantics)

**Focus:** The "Soul" of the world.

**Components:**

### Vector Ideology: Multi-dimensional consciousness
- `IdeologicalProfile` model - class_consciousness, national_identity, agitation
- The George Jackson Refactor - "Fascism is the defensive form of capitalism"
- Agitation Router - crisis energy flows to revolution OR fascism based on solidarity

**Status:** COMPLETE (Sprint 3.4.3)

### Semantic Physics: ChromaDB as a physics engine
- Canon - foundational theoretical texts (Marx, Lenin, Fanon)
- Chronicle - game history (events, state snapshots)
- Zeitgeist - emergent patterns detected by embedding similarity

**Status:** PLANNED

### Resonance: Historical events triggering based on vector similarity
- When current conditions approach historical precedent, trigger narrative
- "The Weimar Resonance" - economic crisis + atomization + agitation = fascism risk

**Status:** PLANNED

**Goal:** A world that "remembers" history and forms complex beliefs.

**Key Insight:** "Agitation without solidarity produces fascism, not revolution."

---

## Phase V: The Interface (Control)

**Focus:** Visualization.

**Components:**
- NiceGUI Dashboard - real-time simulation control
- Map rendering - territorial display with heat overlay
- Graph visualization - relationship network with tension indicators
- History browser - timeline navigation with undo/redo

**Status:** PLANNED

**Goal:** Players can see and interact with the simulation state.

---

## Phase VI: The Fractal (Scale)

**Focus:** Expansion.

**Components:**
- Procedural generation - automatic world creation from parameters
- Multi-region trade - inter-territorial economic flows
- Internal colonies - fractal topology within core (race/gender/geographic stratification)
- Full faction system - multiple competing organizations

**Status:** FUTURE

**Goal:** The simulation scales from 4-node model to full world complexity.

**Key Insight:** "Composite/Graph pattern enables modeling stratification within Core"

---

## Development Model: Base and Superstructure

```
            ┌─────────────────────────────────────┐
            │     SUPERSTRUCTURE                  │
            │  (Phase IV: Semantics)              │
            │  - Ideology Vector Space            │
            │  - Semantic Memory (RAG)            │
            │  - Narrative Generation             │
            └─────────────────────────────────────┘
                           ↑
                           │ Determines consciousness
                           │
            ┌─────────────────────────────────────┐
            │     MATERIAL BASE                   │
            │  (Phase III: Physics)               │
            │  - Economic flows (rent, wages)     │
            │  - Territorial control              │
            │  - Crisis conditions                │
            └─────────────────────────────────────┘
                           ↑
                           │ Built on
                           │
            ┌─────────────────────────────────────┐
            │     TOPOLOGY                        │
            │  (Phase II: Mesh)                   │
            │  - NetworkX graph structure         │
            │  - Entity relationships             │
            │  - System execution order           │
            └─────────────────────────────────────┘
                           ↑
                           │ Implements
                           │
            ┌─────────────────────────────────────┐
            │     KERNEL                          │
            │  (Phase I: Logic)                   │
            │  - Pure math formulas               │
            │  - Pydantic type constraints        │
            │  - TDD proven equations             │
            └─────────────────────────────────────┘
```

---

## Superseded Documents

- `brainstorm/plans/four-phase-engine-blueprint.md` - DEPRECATED (2025-12-09)
- `brainstorm/plans/phase2-game-loop-design.md` - Still valid for Phase II details

---

## Cross-References

| Topic | Document |
|-------|----------|
| Current status | `ai-docs/state.yaml` |
| Architecture | `ai-docs/architecture.yaml` |
| Formulas | `ai-docs/formulas-spec.yaml` |
| Decisions | `ai-docs/decisions.yaml` |
| George Jackson Refactor | `brainstorm/mechanics/fascist_bifurcation.md` |
| Territory System | `brainstorm/mechanics/layer0_territory.md` |

---

*Document created: 2025-12-09*
*Epoch: Six-Phase Fractal Evolution*
