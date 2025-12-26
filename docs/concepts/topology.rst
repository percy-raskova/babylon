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
physical matter. Babylon implements a **4-phase model** that distinguishes
between broad mass movements and disciplined vanguard parties:

**Gaseous State** (percolation ratio < 0.1)
   Atomized leftism. Individual cells operate in isolation. No giant
   component exists. The state can eliminate nodes without cascade effects.
   Consciousness transmission is blocked.

**Transitional State** (0.1 <= ratio < 0.5)
   Emerging structure. Some clusters are forming but no vanguard yet.
   The network is vulnerable to targeted disruption. Consciousness can
   propagate within clusters but not across the full network.

**Liquid State** (ratio >= 0.5 AND cadre_density < 0.5)
   Giant component formed but with weak ties. A **mass movement** has
   emerged but lacks disciplined cadre. Many sympathizers (edges > 0.1)
   but few committed activists (edges > 0.5). Vulnerable to ideological
   drift and internal division. *Historical example: Occupy Wall Street.*

**Solid State** (ratio >= 0.5 AND cadre_density >= 0.5)
   Giant component with strong ties throughout. The **vanguard party**
   has crystallized with iron discipline. Committed cadre dominate the
   network. Can survive repression and maintain ideological coherence.
   *Historical example: The Bolshevik Party (1917).*

The **percolation ratio** is calculated as L_max / N, where L_max is
the size of the largest connected component and N is the total number
of social class nodes.

The **cadre density** is calculated as actual_liquidity / potential_liquidity,
measuring the ratio of committed activists (strong ties) to sympathizers
(weak ties) in the network.

**Phase Transition Events:**

When the percolation ratio or cadre density crosses a threshold boundary,
the :class:`TopologyMonitor` emits a :class:`PhaseTransitionEvent`. This
enables the AI narrative layer to generate prose about organizational
crystallization or fragmentation.

.. code-block:: python

   # Phase transition from mass movement to vanguard party
   event = PhaseTransitionEvent(
       tick=15,
       previous_state="liquid",
       new_state="solid",
       percolation_ratio=0.55,
       cadre_density=0.65,  # Strong cadre discipline
       largest_component_size=11,
   )

**Key Insight:** The distinction between Liquid and Solid phases captures
the tragedy of revolutions that had the numbers but lacked the discipline.
A mass movement (Liquid) can be dispersed by ideological confusion; a
vanguard party (Solid) maintains coherence through repression.

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
