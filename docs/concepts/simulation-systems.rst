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
       A["WorldState (tick N)"] --> B["1. ImperialRentSystem<br/>Extract tribute"]
       B --> C["2. SolidaritySystem<br/>Transmit consciousness"]
       C --> D["3. ConsciousnessSystem<br/>Drift ideology"]
       D --> E["4. SurvivalSystem<br/>Calculate probabilities"]
       E --> F["5. StruggleSystem<br/>Agency responses"]
       F --> G["6. ContradictionSystem<br/>Accumulate tension"]
       G --> H["7. TerritorySystem<br/>Process heat/eviction"]
       H --> I["WorldState (tick N+1)"]

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

The order of systems is not arbitrary—it reflects causal dependencies in the
simulation's theoretical model:

**1. ImperialRentSystem** (Economic base)
   Material conditions must be established first. Wealth flows via
   EXPLOITATION edges determine everything that follows.

**2. SolidaritySystem** (Communication infrastructure)
   Consciousness can only spread where organizational infrastructure
   exists. This must happen before ideology drift.

**3. ConsciousnessSystem** (Superstructure response)
   Ideology changes in response to material conditions and solidarity.
   The George Jackson bifurcation determines revolution vs fascism.

**4. SurvivalSystem** (Agent calculus)
   With economic and ideological state updated, agents can calculate
   their survival probabilities under acquiescence vs revolution.

**5. ContradictionSystem** (Tension accumulation)
   Contradictions between classes accumulate based on the above factors,
   potentially triggering rupture events.

**6. TerritorySystem** (Spatial dynamics)
   State attention (heat) responds to activity, triggering eviction and
   displacement. This is the carceral geography layer.

**7. StruggleSystem** (Agency responses)
   Finally, agents respond to state actions. EXCESSIVE_FORCE can trigger
   UPRISING when organization is sufficient.

Why This Order Matters
~~~~~~~~~~~~~~~~~~~~~~

Consider what happens if we ran systems in wrong order:

- **SolidaritySystem before ImperialRentSystem**: Consciousness would spread
  based on stale wealth data from the previous tick.
- **ConsciousnessSystem before SolidaritySystem**: Bifurcation would check
  for solidarity edges that haven't been updated yet.
- **StruggleSystem before TerritorySystem**: Agents would respond to
  repression that hasn't been applied yet.

The system order encodes the Marxist base-superstructure relationship:
material conditions (base) determine consciousness (superstructure), which
then shapes political action.

The Seven Systems
-----------------

Each system models a specific aspect of class dynamics:

**ImperialRentSystem**
   Extracts wealth via EXPLOITATION edges. Implements the fundamental
   theorem: W_c > V_c implies imperial rent extraction.

**SolidaritySystem**
   Transmits consciousness along SOLIDARITY edges and decays edge
   strengths over time (organization requires maintenance).

**ConsciousnessSystem**
   Applies the George Jackson bifurcation model. Agitation routes to
   revolution (with solidarity) or fascism (without solidarity).

**SurvivalSystem**
   Calculates P(S|A) and P(S|R) for each class. When P(S|R) > P(S|A),
   revolution becomes the rational survival strategy.

**ContradictionSystem**
   Accumulates tension from class contradictions. When tension exceeds
   threshold, flags potential rupture events.

**TerritorySystem**
   Manages territorial heat (state attention), eviction, displacement,
   and the detention-to-incarceration pipeline.

**StruggleSystem**
   Handles agency responses to state action. EXCESSIVE_FORCE against
   organized classes can trigger UPRISING events.

See Also
--------

- :doc:`/reference/systems` - API reference for each system
- :doc:`/how-to/add-custom-system` - Create your own systems
- :doc:`architecture` - Overall engine architecture
- :doc:`imperial-rent` - Economic theory foundation
