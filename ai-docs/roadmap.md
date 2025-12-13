# Babylon Master Roadmap: The Path to MVP & Horizontal Scaling

> "We build the skeleton first. Then we add the muscles. Finally, we teach it to speak."

---

## 0. The Bedrock (COMPLETE)

**Status:** VERIFIED (1,785 Tests)
**Objective:** A deterministic, mathematically consistent simulation kernel.

### The Kernel (Phase I)
- [x] `SocialClass` & `WorldState` Pydantic models
- [x] `formulas.py`: MLM-TW equations (Unequal Exchange, Survival Calculus)
- [x] Constrained types: `Probability`, `Currency`, `Ideology`

### The Mesh (Phase II)
- [x] `SimulationEngine`: System-based architecture
- [x] `NetworkX` integration: Graph topology state
- [x] `ServiceContainer`: Dependency injection pattern

### Testing Infrastructure (Phase 2.5)
- [x] `DomainFactory`: Centralized fixture generation (`tests/factories/domain.py`)
- [x] `BabylonAssert`: Semantic assertions (`tests/assertions.py`)
- [x] `MockMetricsCollector`: Spy pattern (`tests/mocks/metrics_collector.py`)

**Key Insight:** "Graph + Math = History" - The topology encodes relationships, the formulas encode dynamics.

---

## 1. The Material Base - Physics (COMPLETE)

**Status:** IMPLEMENTED
**Objective:** A physically consistent world where material conditions drive events.

### Layer 0: The Territorial Substrate
- [x] `TerritorySystem`: Heat dynamics, eviction pipeline (`systems/territory.py`, 378 lines)
- [x] **Carceral Geography:** Necropolitical Triad (RESERVATION, PENAL_COLONY, CONCENTRATION_CAMP)
- [x] **Dynamic Necropolitics:** `DisplacementPriorityMode` (EXTRACTION vs CONTAINMENT vs ELIMINATION)
- [x] Heat spillover via ADJACENCY edges

### Layer 1: The Imperial Circuit
- [x] `ImperialRentSystem`: Value extraction via TRIBUTE edges
- [x] `SolidaritySystem`: Consciousness transmission via SOLIDARITY edges
- [x] WAGES edge: Super-wages from bourgeoisie to core workers
- [x] CLIENT_STATE edge: Imperial subsidy to comprador

### Agency Layer: The Spark
- [x] `StruggleSystem`: The George Floyd Dynamic (`systems/struggle.py`, 282 lines)
- [x] **The Spark:** EXCESSIVE_FORCE events (stochastic police brutality)
- [x] **The Combustion:** UPRISING when (spark OR p_rev > p_acq) AND agitation > threshold
- [x] **The Result:** SOLIDARITY_SPIKE builds infrastructure for consciousness transmission

**Key Insight:** "State Violence (The Spark) + Accumulated Agitation (The Fuel) = Insurrection (The Explosion)"

---

## 2. The Observer - Logos (COMPLETE)

**Status:** COMPLETE (Sprint 3.3)
**Objective:** Give the engine "eyes." Transition from implicit state changes to explicit, typed Events.

### Implemented Infrastructure
- [x] `SimulationObserver` Protocol (`engine/observer.py`)
- [x] `EventBus`: Pub/sub architecture (`engine/event_bus.py`)
- [x] `EventType` enum: 11 typed events (`models/enums.py`)
  - Economic: SURPLUS_EXTRACTION, IMPERIAL_SUBSIDY, ECONOMIC_CRISIS
  - Consciousness: SOLIDARITY_AWAKENING, CONSCIOUSNESS_TRANSMISSION, MASS_AWAKENING
  - Struggle: EXCESSIVE_FORCE, UPRISING, SOLIDARITY_SPIKE
  - Contradiction: RUPTURE
  - Topology: PHASE_TRANSITION
- [x] `TopologyMonitor`: Phase transition detection via percolation theory (`engine/topology_monitor.py`)
- [x] `TopologySnapshot` models: Frozen metrics per tick (`models/topology_metrics.py`)

### Completed Sprints
- [x] **Sprint 3.1:** `SimulationEvent` Pydantic Schema (COMPLETE)
  - *Delivered:* `src/babylon/models/events.py` with `SimulationEvent`, `EconomicEvent`, `ExtractionEvent`
  - *Delivered:* `WorldState.events: list[SimulationEvent]` field for typed event persistence
  - *Delivered:* `_convert_bus_event_to_pydantic()` in SimulationEngine for EventBus → Pydantic conversion
  - *Delivered:* Test infrastructure updates (`DomainFactory.create_extraction_event()`, `Assert.has_event()`)
- [x] **Sprint 3.1+:** Event Type Expansion (COMPLETE)
  - *Delivered:* 3 base classes: `ConsciousnessEvent`, `StruggleEvent`, `ContradictionEvent`
  - *Delivered:* 8 concrete events: `SubsidyEvent`, `CrisisEvent`, `TransmissionEvent`, `MassAwakeningEvent`, `SparkEvent`, `UprisingEvent`, `SolidaritySpikeEvent`, `RuptureEvent`
  - *Delivered:* `_convert_bus_event_to_pydantic()` handles all 10 EventTypes
  - *Delivered:* Factory methods for all event types in `DomainFactory`
- [x] **Sprint 3.3:** Topology Events (COMPLETE)
  - *Delivered:* `PHASE_TRANSITION` EventType (11 total)
  - *Delivered:* `TopologyEvent` and `PhaseTransitionEvent` models
  - *Delivered:* `TopologyMonitor._classify_phase()` for gaseous/transitional/liquid states
  - *Delivered:* `TopologyMonitor.get_pending_events()` for event collection
  - *Delivered:* `Simulation._collect_observer_events()` for observer event injection
  - *Delivered:* Observer events injected into next tick via `persistent_context['_observer_events']`

**Key Insight:** ADR003 - "AI failures don't break game mechanics."

---

## 3. The Narrator - Mythos (PLANNED)

**Status:** DESIGNED
**Objective:** Give the engine a "voice."

### The Bridge
- [ ] `NarrativeDirector`: Interface between Engine and LLM
- [ ] `PromptBuilder`: Context assembly using `WorldState` + `SimulationEvent`

### The Voice
- [ ] **Sprint 4.1:** Character Sheet Integration (Percy Raskova)
- [ ] **Sprint 4.2:** Historical RAG (ChromaDB) to ground events in precedent
  - "The Weimar Resonance" - economic crisis + atomization + agitation = fascism risk

**Key Insight:** "Agitation without solidarity produces fascism, not revolution."

---

## 4. The Interface - MVP (PLANNED)

**Status:** DESIGNED
**Objective:** The "Digital Grow Room" aesthetic.

### The Monitor Station
- [ ] **NiceGUI** implementation
- [ ] **Topology Scanner:** ECharts graph visualization (Cyber-insurgency style)
- [ ] **Tension Gauge:** Analog visual for `ContradictionSystem` accumulation

### Controls
- [ ] "Agitation" Fan Speed Slider
- [ ] "Rent Extraction" Voltage Dial

### MVP Definition

> A stable loop where a player can tweak "Repression", watch the `StruggleSystem` trigger a spark, see the `TerritorySystem` evict populations to a Penal Colony, and read a Narrative Log explaining the resulting riot.

**Key Insight:** "The bomb factory pays well. That's the problem."

---

## 5. Horizontal Expansion (FUTURE)

**Status:** SPECIFIED (Brainstorming)
**Objective:** Once MVP is stable, we "plug in" these new Systems. The Engine architecture supports this via `systems: list[System]`.

### System A: Kinetic Warfare (Asymmetric Logistics)

*Based on: `brainstorm/mechanics/kinetic_warfare.md`*

**Concept:** Not frontlines, but system disruption.

**The Target Triad:**
1. **Nodes of Extraction:** Mines/Farms (Vulnerable to strikes)
2. **Edges of Circulation:** Logistics/Power lines (Sabotage cuts value flow)
3. **Nodes of Realization:** Data Centers/Bunkers (High security)

**Mechanic:** Player spends `LaborPower` to target specific graph nodes. Success checks against `State.security_level`.

### System B: The Metabolism (Resource System)

*Based on: `brainstorm/mechanics/resource-system.md`*

**Concept:** Every movement needs Mana (Action) and HP (Coherence).

**Resource 1: Labor-Power (LP):**
- Generated by: Organized Workers + Base Areas
- Spent on: Agitation, Attacks, Building Edges

**Resource 2: Coherence (Entropy):**
- Natural decay over time (Entropy)
- Maintained by: Rituals, Theory, Victories
- *Failure State:* High LP + Low Coherence = Ultra-leftism (action without effect)

### System C: Liberation Mechanics

*Extension of: `src/babylon/engine/systems/territory.py`*

**Concept:** Reversing the Carceral Geography.

**Mechanic:** Converting a `PENAL_COLONY` or `CONCENTRATION_CAMP` back into a `PERIPHERY` node.

**Requirements:**
- `StruggleSystem` Uprising event *inside* the sink node
- External `KineticWarfare` breach of the node's defenses

---

## The Horizontal Guarantee

We can add **System A**, **System B**, and **System C** without breaking the existing MVP because:

1. **Shared State:** They read/write to the same `WorldState` graph
2. **Event Coupling:** They communicate via the `EventBus` (e.g., `SabotageEvent` triggers `EconomicSystem` recalc)
3. **No Monolith:** `SimulationEngine` simply iterates through `[Territory, Economy, Struggle, Warfare, Metabolism]`

```
SimulationEngine.run_tick(graph, services, context)
     |
     +-- 1. ImperialRentSystem      (economic base)
     +-- 2. SolidaritySystem        (consciousness transmission)
     +-- 3. ConsciousnessSystem     (ideology drift)
     +-- 4. SurvivalSystem          (P(S|A), P(S|R) calculations)
     +-- 5. StruggleSystem          (Agency Layer)
     +-- 6. ContradictionSystem     (tension/rupture dynamics)
     +-- 7. TerritorySystem         (spatial superstructure)
     +-- 8. WarfareSystem           (FUTURE: kinetic logistics)
     +-- 9. MetabolismSystem        (FUTURE: LP/Coherence)
```

---

## Development Model: Base and Superstructure

```
            +---------------------------------------------+
            |     INTERFACE (Phase 4: MVP)                |
            |  - NiceGUI Dashboard                        |
            |  - Topology Scanner                         |
            |  - Tension Gauge                            |
            +---------------------------------------------+
                           |
                           | Renders
                           v
            +---------------------------------------------+
            |     NARRATOR (Phase 3: Mythos)              |
            |  - NarrativeDirector                        |
            |  - Historical RAG                           |
            |  - Character Sheets                         |
            +---------------------------------------------+
                           |
                           | Observes
                           v
            +---------------------------------------------+
            |     OBSERVER (Phase 2: Logos)               |
            |  - SimulationObserver Protocol              |
            |  - EventBus (11 EventTypes)                 |
            |  - TopologyMonitor (Phase Transitions)      |
            +---------------------------------------------+
                           |
                           | Watches
                           v
            +---------------------------------------------+
            |     MATERIAL BASE (Phase 1: Physics)        |
            |  - TerritorySystem (Carceral Geography)     |
            |  - ImperialRentSystem (Value Extraction)    |
            |  - StruggleSystem (Agency Layer)            |
            +---------------------------------------------+
                           |
                           | Built on
                           v
            +---------------------------------------------+
            |     BEDROCK (Phase 0: Kernel + Mesh)        |
            |  - Pure math formulas                       |
            |  - Pydantic type constraints                |
            |  - NetworkX graph structure                 |
            |  - TDD proven equations (1,785 tests)       |
            +---------------------------------------------+
```

---

## Cross-References

| Topic | Document |
|-------|----------|
| Current status | `ai-docs/state.yaml` |
| Architecture | `ai-docs/architecture.yaml` |
| Formulas | `ai-docs/formulas-spec.yaml` |
| Observer Layer | `ai-docs/observer-layer.yaml` |
| Decisions | `ai-docs/decisions.yaml` |
| George Jackson Refactor | `brainstorm/mechanics/fascist_bifurcation.md` |
| Territory System | `brainstorm/mechanics/layer0_territory.md` |
| Carceral Geography | `brainstorm/mechanics/carceral_geography.md` |
| Agency Layer | `brainstorm/mechanics/agency_layer.md` |
| Kinetic Warfare | `brainstorm/mechanics/kinetic_warfare.md` |
| Resource System | `brainstorm/mechanics/resource-system.md` |

---

## Superseded Documents

- `brainstorm/plans/four-phase-engine-blueprint.md` - DEPRECATED (2025-12-09)
- Previous "Six-Phase Fractal Evolution" structure - SUPERSEDED (2025-12-12)

---

*Document created: 2025-12-09*
*Last updated: 2025-12-12 (Sprint 3.3 Topology Events Complete)*
*Epoch: MVP & Horizontal Scaling*
