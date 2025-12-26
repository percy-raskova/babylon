# Babylon Master Roadmap: The Path to MVP & Horizontal Scaling

> "We build the skeleton first. Then we add the muscles. Finally, we teach it to speak."

---

## 0. The Bedrock (COMPLETE)

**Status:** VERIFIED (1,926 Tests)
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

## 3. The Narrator - Mythos (IN PROGRESS)

**Status:** IN PROGRESS (Sprint 4.1 Complete)
**Objective:** Give the engine a "voice."

### The Bridge (COMPLETE)
- [x] `NarrativeDirector`: Interface between Engine and LLM
  - Now consumes typed `SimulationEvent` objects via `state.events`
  - `SEMANTIC_MAP` uses `EventType` enum keys for theoretical context
  - `SIGNIFICANT_EVENT_TYPES` filters narrative-worthy events
- [x] `PromptBuilder`: Context assembly using `WorldState` + `SimulationEvent`
  - `build_context_block()` accepts `list[SimulationEvent]`
  - `_format_event()` method with match/case for all event types
  - Rich formatting for PhaseTransitionEvent, CrisisEvent, SparkEvent, etc.

### The Voice
- [ ] **Sprint 4.2:** Character Sheet Integration (Percy Raskova)
- [ ] **Sprint 4.3:** Historical RAG (ChromaDB) to ground events in precedent
  - "The Weimar Resonance" - economic crisis + atomization + agitation = fascism risk

### Completed Sprints
- [x] **Sprint 4.1:** The Narrative Bridge (Typed Event Pipeline)
  - `PromptBuilder` accepts typed events, formats per event type
  - `NarrativeDirector` uses `state.events` instead of `event_log` strings
  - 9 new integration tests in `test_narrative_pipeline.py`
  - Commit: `d756498`

**Key Insight:** "Agitation without solidarity produces fascism, not revolution."

---

## 4. The Interface - MVP (IN PROGRESS)

**Status:** IN PROGRESS (Developer Dashboard Functional)
**Objective:** The "Digital Grow Room" aesthetic - Bunker Constructivism UI.
**Design System:** `ai-docs/design-system.yaml` (Source of Truth)

### Developer Dashboard (COMPLETE)
- [x] Main Window Layout (NiceGUI root function pattern, ADR026)
- [x] 4-Panel Grid Layout: TrendPlotter (left), Narrative+Log (center), StateInspector (right)
- [x] AsyncSimulationRunner for non-blocking UI during PLAY mode
- [x] ControlDeck: STEP/PLAY/PAUSE/RESET buttons with tick counter
- [x] TrendPlotter: ECharts time-series metrics visualization
- [x] NarrativeTerminal: Typewriter effect for narrative display
- [x] SystemLog: Event log with auto-scroll
- [x] StateInspector: JSON editor for WorldState inspection
- [x] Subcutaneous integration tests (mocked NiceGUI components)
- [x] CSS Grid/Flexbox layout fix: w-full propagation for flex-1 children

### Phase 4.1: The Living Circuit (Vertical Integration) - IN PROGRESS

**Diagnosis:** Dashboard exists but shows flat metrics. Root cause: using 2-node scenario instead of 4-node Imperial Circuit.

**Mantra:** "A flat line on a fancy graph is still a flat line."

#### Sprint 4.1A: Wire the Circuit
- [ ] Switch `main.py` to use `create_imperial_circuit_scenario()`
- [ ] Verify 4 nodes in StateInspector: P_w, P_c, C_b, C_w
- [ ] Verify 5 edges: EXPLOITATION, TRIBUTE, WAGES, CLIENT_STATE, SOLIDARITY

#### Sprint 4.1B: Expose Meaningful Metrics
- [ ] TrendPlotter: 4 wealth lines (color-coded by SocialRole)
- [ ] TrendPlotter: Consciousness differential (P_w - C_w)
- [ ] TrendPlotter: Solidarity edge strength over time
- [ ] TrendPlotter: Imperial rent pool level
- [ ] SystemLog: Filter for SIGNIFICANT_EVENT_TYPES

#### Sprint 4.1C: Tune for Crisis
- [ ] GameDefines: faster consciousness drift
- [ ] GameDefines: higher tension accumulation
- [ ] Test Fascist Bifurcation (solidarity_strength = 0)
- [ ] Test Revolutionary path (solidarity_strength > 0)
- [ ] Verify George Floyd Dynamic spark mechanics
- [ ] **Goal:** Crisis within 30-50 ticks

### Sprint 4.2: The Panopticon Shell (Deferred)
- [x] Main Window Layout (NiceGUI root function pattern, ADR026)
- [ ] Global CSS (Fonts, Scrollbars, CSS Variables from design-system.yaml)
- [ ] CRT Overlay effect (scanlines, vignette via Tailwind pseudo-elements)
- [x] The Event Log (ReadOnly terminal at bottom, data_green text)

### Sprint 4.3: The Prism Feed
- [ ] NarrativeDirector integration with UI
- [ ] "Propaganda Card" component implementation (purple signal stripe)
- [ ] Purple grow_light styling for AI-generated content
- [ ] Narrative streaming display

### Sprint 4.4: The Scanner
- [ ] NetworkX visualization (ECharts or D3)
- [ ] Node styling by class type (SocialClass vs Territory)
- [ ] Edge visualization (EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE)
- [ ] Interactive zoom/pan controls

### Controls (Future)
- [ ] "Agitation" Fan Speed Slider
- [ ] "Rent Extraction" Voltage Dial
- [ ] "Repression" Dial

### MVP Definition

> A stable loop where a player can tweak "Repression", watch the `StruggleSystem` trigger a spark, see the `TerritorySystem` evict populations to a Penal Colony, and read a Narrative Log explaining the resulting riot.

**Key Insight:** "The bomb factory pays well. That's the problem."
**Design Mantras:** "Red is Pain, not Decoration" | "Purple is Life, Green is Data" | "The Screen is a Physical Object"

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

**Concept:** Every movement needs Mana (Action) and HP (Coherence).

**Resource 1: Labor-Power (LP):**
- Generated by: Organized Workers + Base Areas
- Spent on: Agitation, Attacks, Building Edges

## The Horizontal Guarantee

We can add **System A**, **System B**, **System C**, and **System D** without breaking the existing MVP because:

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

### System D: Reproductive Labor (Social Reproduction)

*Based on: `brainstorm/reproductive-labor-theory.md`, `ai-docs/reproductive-labor.yaml`*

**Concept:** Model the invisible labor that reproduces labor power.

**Theoretical Basis:** Marx (Capital Vol I), Engels (Origin of Family), Marxist Feminist Theory (Federici, Combahee River Collective)

**Key Insight:** "Women's unpaid domestic labor, emotional labor, and reproductive labor subsidizes capital accumulation by reproducing labor power at NO COST to capital."

**Three-Tier Implementation:**

| Tier | Components | Status |
|------|------------|--------|
| 1 | Subsistence floor, regeneration rate, capped extraction | PLANNED |
| 2 | Debt mechanism, extraction efficiency, reproduction pressure metric | PLANNED |
| 3 | Gendered sub-agents, State mediator, household units | DEFERRED |

**Mechanic (Tier 1):**
- Workers have a `subsistence_floor` below which extraction is capped
- Workers regenerate wealth up to floor via `regeneration_rate`
- SOLIDARITY edges provide `solidarity_regeneration_bonus`
- Atomized workers regenerate slower (no community mutual aid)

**System Position:**
```
SimulationEngine.run_tick(graph, services, context)
     +-- 1. ImperialRentSystem      (extraction with subsistence cap)
     +-- 2. ReproductionSystem      (NEW: regeneration via reproductive labor)
     +-- 3. SolidaritySystem        (consciousness transmission)
     ...
```

---

## The Horizontal Guarantee

We can add **System A**, **System B**, **System C**, and **System D** without breaking the existing MVP because:

1. **Shared State:** They read/write to the same `WorldState` graph
2. **Event Coupling:** They communicate via the `EventBus` (e.g., `SabotageEvent` triggers `EconomicSystem` recalc)
3. **No Monolith:** `SimulationEngine` simply iterates through `[Territory, Economy, Struggle, Warfare, Metabolism]`

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
            |  - TDD proven equations (1,926 tests)       |
            +---------------------------------------------+
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
*Last updated: 2025-12-25 (Developer Dashboard Functional)*
*Epoch: MVP & Horizontal Scaling*
