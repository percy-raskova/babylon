Simulation Systems Architecture
===============================

This document explains **why** Babylon's simulation engine uses modular systems
and how they work together to produce emergent class struggle dynamics.

The Modular System Design
-------------------------

Each simulation tick, the engine runs a sequence of **Systems** that
transform the world state. This design choice enables:

1. **Testability** - Each system can be unit tested in isolation
2. **Composability** - Systems can be added, removed, or reordered
3. **Clarity** - Each system has a single responsibility

.. mermaid::

   flowchart TB
       A["WorldState (tick N)"] --> B["1. VitalitySystem<br/>Drain + attrition"]
       B --> C["2. TerritorySystem<br/>Heat/eviction"]
       C --> D["3. ProductionSystem<br/>Value creation"]
       D --> E["4. SolidaritySystem<br/>Transmit consciousness"]
       E --> F["5. ImperialRentSystem<br/>Extract tribute"]
       F --> G["6. DecompositionSystem<br/>LA crisis"]
       G --> H["7. ControlRatioSystem<br/>Guard ratio"]
       H --> I["8. MetabolismSystem<br/>Ecology"]
       I --> J["9. SurvivalSystem<br/>P(S|A), P(S|R)"]
       J --> K["10. StruggleSystem<br/>Agency"]
       K --> L["11. ConsciousnessSystem<br/>Bifurcation"]
       L --> M["12. ContradictionSystem<br/>Tension"]
       M --> N["WorldState (tick N+1)"]

The System Protocol
-------------------

All systems implement a common protocol that enforces separation of concerns:

.. code-block:: python

   class System(Protocol):
       def step(
           self,
           graph: nx.DiGraph[str],
           services: ServiceContainer,
           context: ContextType,  # Union[dict[str, Any], TickContext]
       ) -> None:
           """Mutate graph according to system logic."""
           ...

**Why this contract?**

- **Graph-only mutation**: Systems transform the topology directly, ensuring
  all state changes are visible and traceable through the graph structure.
- **No inter-tick state**: Systems are stateless between ticks, preventing
  hidden dependencies and making behavior deterministic.
- **Service injection**: Shared services (EventBus, FormulaRegistry) are
  injected, enabling testing with mocks and runtime swapping.

System Execution Order
----------------------

The order of systems is not arbitrary—it reflects **materialist causality**:
physical reality (life, space, production) determines social responses
(consciousness, struggle), not vice versa.

The twelve systems execute in three phases:

**Phase 1: Material Base** (Systems 1-8)
   Physical existence precedes consciousness. These systems model the
   objective conditions that constrain all social action.

**Phase 2: Superstructure** (Systems 9-12)
   Agents respond to material conditions through survival calculations,
   struggle, ideological drift, and contradiction accumulation.

**Phase 3: Why Order Matters**
   Material base must update before superstructure can respond. Running
   systems out of order produces incoherent state (e.g., consciousness
   spreading based on stale wealth data).

The Twelve Systems
------------------

Each system models a specific aspect of class dynamics:

**1. VitalitySystem** (Material Base)
   The Drain (subsistence costs), Grinding Attrition (slow vitality decay),
   and The Reaper (death when vitality reaches zero). Physical existence is
   the foundation of all else.

**2. TerritorySystem** (Material Base)
   Heat dynamics (state attention), eviction pipeline, and necropolitics.
   Space is contested through carceral geography.

**3. ProductionSystem** (Material Base)
   Value creation from labor × biocapacity. Production is the interface
   between human labor and ecological limits.

**4. SolidaritySystem** (Material Base)
   Transmits consciousness along SOLIDARITY edges. Organization is a
   material infrastructure that requires maintenance.

**5. ImperialRentSystem** (Material Base)
   5-phase Imperial Circuit with pool tracking. Implements the fundamental
   theorem: W_c > V_c implies imperial rent extraction from periphery.

**6. DecompositionSystem** (Crisis Dynamics)
   Labor aristocracy decomposition during super-wage crisis. Models the
   breakdown of core working class privilege.

**7. ControlRatioSystem** (Crisis Dynamics)
   Guard-to-prisoner ratio monitoring. When ratio exceeds threshold,
   bourgeoisie makes terminal decision (massacre vs collapse).

**8. MetabolismSystem** (Material Base)
   Biocapacity depletion and ecological overshoot. Ecological limits
   constrain capital accumulation.

**9. SurvivalSystem** (Superstructure)
   Calculates P(S|A) and P(S|R) for each class. When P(S|R) > P(S|A),
   revolution becomes the rational survival strategy.

**10. StruggleSystem** (Superstructure)
   George Floyd Dynamic: agency responses to state action. EXCESSIVE_FORCE
   against organized classes can trigger UPRISING events.

**11. ConsciousnessSystem** (Superstructure)
   Ideological drift and George Jackson bifurcation. Agitation routes to
   revolution (with solidarity) or fascism (without solidarity).

**12. ContradictionSystem** (Superstructure)
   Accumulates tension from class contradictions. When tension exceeds
   threshold, flags potential rupture events.

See Also
--------

- :doc:`/reference/systems` - API reference for each system
- :doc:`/how-to/add-custom-system` - Create your own systems
- :doc:`architecture` - Overall engine architecture
- :doc:`imperial-rent` - Economic theory foundation
