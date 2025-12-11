Carceral Geography
==================

Carceral Geography models the spatial dimensions of state repression:
where populations are detained, displaced, and eliminated. It implements
the **detention pipeline** and **displacement routing** systems.

Overview
--------

The carceral geography system tracks how the state uses space as a tool
of class management:

- **Detention** - Removing populations from economic circulation
- **Displacement** - Forcing populations to move between territories
- **Elimination** - Permanent removal from the simulation

This models real-world patterns: mass incarceration, gentrification,
border enforcement, and colonial dispossession.

The Detention Pipeline
----------------------

When state repression targets a class, it enters a three-stage pipeline:

.. mermaid::

   stateDiagram-v2
       [*] --> DETENTION: Arrest
       DETENTION --> INCARCERATION: After detention_duration
       INCARCERATION --> ELIMINATION: displacement_priority
       DETENTION --> [*]: Release
       INCARCERATION --> [*]: Labor scarce mode

       note right of DETENTION: Short-term hold<br/>Can be released
       note right of INCARCERATION: Long-term hold<br/>Reduced capacity
       note right of ELIMINATION: Removed from<br/>simulation

**Stage Transitions:**

1. **Detention → Incarceration**
   After ``detention_duration`` ticks, detained classes move to incarceration.

2. **Incarceration → Elimination/Release**
   Based on ``displacement_priority`` mode:
   - ELIMINATION mode: Classes are eliminated
   - LABOR_SCARCE mode: Classes are released (needed for production)
   - BALANCED mode: Probabilistic outcome

Displacement Priority Modes
---------------------------

The ``displacement_priority`` parameter controls how the state manages
surplus populations:

.. list-table:: Displacement Priority Modes
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - Logic
     - Historical Parallel
   * - LABOR_SCARCE
     - Prefer release; labor is valuable
     - Post-war labor shortages
   * - BALANCED
     - Mixed approach based on conditions
     - Normal capitalist state
   * - ELIMINATION
     - Prefer elimination; populations disposable
     - Settler colonialism, fascism

**Dynamic Mode Selection:**

The mode can be set statically or computed dynamically based on
economic conditions:

.. code-block:: python

   def calculate_displacement_priority(territory, graph):
       """Dynamic priority based on labor market."""
       labor_supply = count_available_workers(territory, graph)
       labor_demand = calculate_production_needs(territory, graph)

       if labor_supply < labor_demand * 0.5:
           return DisplacementPriority.LABOR_SCARCE
       elif labor_supply > labor_demand * 1.5:
           return DisplacementPriority.ELIMINATION
       else:
           return DisplacementPriority.BALANCED

Territory Heat System
---------------------

Territories accumulate **heat** from high-profile activities:

.. math::

   H_{t+1} = H_t + \Delta H_{activity} - \Delta H_{decay}

**Heat Sources:**

- Protests, strikes (high heat gain)
- Organizing activities (medium heat gain)
- Normal economic activity (no heat change)

**Heat Consequences:**

.. list-table:: Heat Thresholds
   :header-rows: 1
   :widths: 20 80

   * - Heat Level
     - Consequence
   * - < 0.4
     - Normal operations
   * - 0.4 - 0.8
     - Increased surveillance
   * - >= 0.8
     - **Eviction trigger** - classes must relocate

Eviction and Spillover
----------------------

When territory heat reaches 0.8, the **eviction pipeline** activates:

1. **Mark for Eviction**
   Classes with TENANCY edges to hot territory are flagged.

2. **Find Adjacent Territory**
   System searches ADJACENCY edges for relocation targets.

3. **Execute Displacement**
   Classes move to adjacent territory; heat spillover occurs.

.. code-block:: python

   def process_eviction(class_id, hot_territory, graph):
       """Execute eviction from hot territory."""
       # Find adjacent territories
       adjacent = [
           t for t in graph.neighbors(hot_territory)
           if graph.edges[hot_territory, t].get("edge_type") == EdgeType.ADJACENCY
       ]

       if adjacent:
           # Move to lowest-heat adjacent territory
           target = min(adjacent, key=lambda t: graph.nodes[t]["heat"])
           relocate_class(class_id, hot_territory, target, graph)

           # Heat spillover
           graph.nodes[target]["heat"] += SPILLOVER_COEFFICIENT
       else:
           # No escape route - enter detention
           enter_detention(class_id, hot_territory, graph)

Operational Profiles
--------------------

Territories have operational profiles that affect heat dynamics:

.. list-table:: Operational Profiles
   :header-rows: 1
   :widths: 20 30 50

   * - Profile
     - Heat Gain Rate
     - Description
   * - HIGH_PROFILE
     - High
     - Visible areas (city centers, protest sites)
   * - MIXED
     - Medium
     - Normal urban/suburban areas
   * - LOW_PROFILE
     - Low
     - Hidden areas (rural, underground)

**Strategic Implications:**

- Organize in LOW_PROFILE territories to avoid heat
- HIGH_PROFILE territories draw state attention but enable mass mobilization
- Movement between profiles affects surveillance exposure

Integration with Other Systems
------------------------------

Carceral geography interacts with:

**Survival System**
   Detention reduces P(S|A) - survival by acquiescence becomes impossible
   while detained. This can trigger revolutionary consciousness.

**Solidarity System**
   Detained classes lose SOLIDARITY edges (network fragmentation).
   Prison organizing can rebuild them.

**Contradiction System**
   Mass incarceration increases systemic tension. When detention
   capacity is exceeded, contradictions intensify.

Implementation
--------------

The carceral geography system is implemented in ``TerritorySystem``:

.. code-block:: python

   # src/babylon/engine/systems/territory.py

   class TerritorySystem:
       def process(self, graph, services, context):
           # 1. Update heat based on activities
           self._update_heat(graph)

           # 2. Process evictions from hot territories
           self._process_evictions(graph)

           # 3. Advance detention pipeline
           self._advance_detention(graph, context.config)

           # 4. Route displaced populations
           self._route_displacement(graph, context.config)

Key Configuration
-----------------

``GameDefines`` parameters for carceral geography:

.. list-table:: Configuration Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Effect
   * - ``territory.heat_threshold``
     - 0.8
     - Heat level triggering eviction
   * - ``territory.heat_decay``
     - 0.1
     - Heat reduction per tick
   * - ``territory.spillover_coefficient``
     - 0.2
     - Heat transferred on spillover
   * - ``territory.detention_duration``
     - 5
     - Ticks before detention → incarceration
   * - ``territory.displacement_priority``
     - BALANCED
     - Default displacement mode

See Also
--------

- :doc:`/concepts/topology` - Territory nodes and ADJACENCY edges
- :doc:`/concepts/survival-calculus` - How detention affects survival
- :doc:`/concepts/george-jackson-model` - Prison as consciousness crucible
- :doc:`/reference/formulas` - Heat and territory formulas
- :doc:`/reference/configuration` - Territory GameDefines parameters
- :py:mod:`babylon.engine.systems.territory` - Implementation details
