Topology
========

Babylon uses graph topology to represent relationships between classes,
territories, and other entities.

The Graph Model
---------------

The simulation maintains a NetworkX directed graph where:

**Nodes** represent entities:
  - ``SocialClass`` - Classes with economic and ideological attributes
  - ``Territory`` - Spatial locations with heat and profile attributes

**Edges** represent relationships:
  - ``EXPLOITATION`` - Economic extraction relationships
  - ``SOLIDARITY`` - Class consciousness connections
  - ``WAGES`` - Labor-wage relationships
  - ``TRIBUTE`` - Imperial tribute flows
  - ``TENANCY`` - Class-territory occupation
  - ``ADJACENCY`` - Territorial proximity

State Transformation
--------------------

The system uses a pattern of transforming between representations:

.. code-block:: python

   # Convert Pydantic state to graph
   graph = world_state.to_graph()

   # Run simulation systems on graph
   engine.run_tick(graph, services, context)

   # Convert back to Pydantic state
   new_state = WorldState.from_graph(graph)

This allows the simulation engine to work with fluid graph operations
while maintaining strict data validation through Pydantic models.

Solidarity Networks
-------------------

**Solidarity edges** are critical for consciousness transmission:

- Agitation spreads along SOLIDARITY edges
- Without SOLIDARITY, wage falls produce national identity (fascism)
- With SOLIDARITY, wage falls produce class consciousness

This implements the **George Jackson model** of ideological routing.

Territory Heat
--------------

Territories have a **heat** attribute representing state attention:

- HIGH_PROFILE activities increase heat
- LOW_PROFILE activities decrease heat
- Heat >= 0.8 triggers eviction pipeline
- Evicted classes spill over to adjacent territories

Phase States & Percolation
--------------------------

The solidarity network undergoes **phase transitions** analogous to
physical matter:

**Gaseous State** (percolation ratio < 0.1)
   Atomized leftism. Individual cells operate in isolation. No giant
   component exists. The state can eliminate nodes without cascade effects.
   Consciousness transmission is blocked.

**Transitional State** (0.1 <= ratio < 0.5)
   Emerging structure. Some clusters are forming but no vanguard yet.
   The network is vulnerable to targeted disruption. Consciousness can
   propagate within clusters but not across the full network.

**Liquid State** (ratio >= 0.5)
   Giant component formed. The vanguard party has crystallized from
   gaseous leftism. Coordinated action is possible across the network.
   Removal of individual nodes doesn't destroy organizational capacity.

The **percolation ratio** is calculated as L_max / N, where L_max is
the size of the largest connected component and N is the total number
of social class nodes.

**Phase Transition Events:**

When the percolation ratio crosses a threshold boundary, the
:class:`TopologyMonitor` emits a :class:`PhaseTransitionEvent`. This
enables the AI narrative layer to generate prose about organizational
crystallization or fragmentation.

.. code-block:: python

   # Phase transition from atomized to organized
   event = PhaseTransitionEvent(
       tick=15,
       previous_state="gaseous",
       new_state="liquid",
       percolation_ratio=0.55,
       largest_component_size=11,
   )

**Key Insight:** The moment of phase transition is critical. Like water
freezing, there is gradual temperature drop (consciousness accumulation)
followed by sudden phase change (organizational crystallization).

Resilience Testing
------------------

The :class:`TopologyMonitor` can simulate state repression via
**purge tests**:

1. Remove 20% of high-centrality nodes (targeted repression)
2. Check if giant component survives at 40% of original size
3. If test fails: "Sword of Damocles" - movement is fragile

Movements with **star topology** (charismatic leader) are fragile.
Movements with **mesh topology** (distributed leadership) are resilient.

Implementation
--------------

See :py:class:`babylon.models.world_state.WorldState` for the core
state model and graph transformation methods.

See :doc:`/reference/topology` for the TopologyMonitor API reference.

See :doc:`/concepts/percolation-theory` for the mathematical foundations.
