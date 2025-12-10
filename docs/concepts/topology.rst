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

Implementation
--------------

See :py:class:`babylon.models.world_state.WorldState` for the core
state model and graph transformation methods.
