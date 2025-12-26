Simulation Systems Reference
============================

API reference for Babylon's seven core simulation systems.

System Protocol
---------------

All systems implement this protocol:

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

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Description
   * - ``graph``
     - NetworkX DiGraph to mutate (nodes are string IDs)
   * - ``services``
     - Dependency injection container (config, formulas, event_bus, database, defines)
   * - ``context``
     - Mutable dict with ``"tick"`` key and any persistent state

System Execution Order
----------------------

.. list-table::
   :header-rows: 1
   :widths: 5 25 70

   * - #
     - System
     - Purpose
   * - 1
     - ImperialRentSystem
     - Extract wealth via EXPLOITATION edges
   * - 2
     - SolidaritySystem
     - Transmit consciousness via SOLIDARITY edges
   * - 3
     - ConsciousnessSystem
     - Apply George Jackson bifurcation to ideology
   * - 4
     - SurvivalSystem
     - Calculate P(S|A) and P(S|R)
   * - 5
     - StruggleSystem
     - Handle agency responses (EXCESSIVE_FORCE → UPRISING)
   * - 6
     - ContradictionSystem
     - Accumulate tension, flag ruptures
   * - 7
     - TerritorySystem
     - Process heat, eviction, displacement

ImperialRentSystem
------------------

:py:class:`babylon.engine.systems.economic.ImperialRentSystem`

**Purpose:** Extract wealth via EXPLOITATION edges.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - EXPLOITATION edges, tribute rates
   * - **Outputs**
     - Updated wealth values, TRIBUTE edge flows

**Logic:**

.. code-block:: python

   for edge in graph.edges(data=True):
       if edge["edge_type"] == EdgeType.EXPLOITATION:
           tribute = edge["rate"] * source_wealth
           graph.nodes[target]["wealth"] -= tribute
           graph.nodes[source]["wealth"] += tribute

SolidaritySystem
----------------

:py:class:`babylon.engine.systems.solidarity.SolidaritySystem`

**Purpose:** Transmit class consciousness via SOLIDARITY edges.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - SOLIDARITY edges, consciousness values
   * - **Outputs**
     - Updated consciousness, decayed solidarity strengths

**Logic:**

.. code-block:: python

   # Consciousness spreads along SOLIDARITY edges
   for edge in solidarity_edges:
       source_consciousness = graph.nodes[source]["consciousness"]
       transmission = source_consciousness * transmission_rate
       graph.nodes[target]["consciousness"] += transmission

   # Solidarity edges decay over time
   for edge in solidarity_edges:
       edge["solidarity_strength"] *= decay_rate

ConsciousnessSystem
-------------------

:py:class:`babylon.engine.systems.ideology.ConsciousnessSystem`

**Purpose:** Apply George Jackson bifurcation to ideology.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Agitation levels, SOLIDARITY presence
   * - **Outputs**
     - Updated ideology values (-1 to +1)

**Logic:**

.. code-block:: python

   # Determine direction from solidarity network
   has_solidarity = any(
       e for e in graph.edges(node)
       if e["edge_type"] == EdgeType.SOLIDARITY
   )
   direction = -1 if has_solidarity else +1

   # Apply consciousness drift
   drift = drift_sensitivity * agitation * direction
   graph.nodes[node]["ideology"] = clamp(ideology + drift, -1, 1)

**Bifurcation:**

- With solidarity: drift toward -1 (revolutionary)
- Without solidarity: drift toward +1 (fascist)

SurvivalSystem
--------------

:py:class:`babylon.engine.systems.survival.SurvivalSystem`

**Purpose:** Calculate survival probabilities.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Wealth, organization, repression values
   * - **Outputs**
     - Updated P_acquiescence, P_revolution values

**Logic:**

.. code-block:: python

   # Survival by acquiescence
   P_S_A = sigmoid(wealth - subsistence_threshold)

   # Survival by revolution
   P_S_R = organization / max(repression, epsilon)

   graph.nodes[node]["P_acquiescence"] = P_S_A
   graph.nodes[node]["P_revolution"] = P_S_R

**Rupture condition:** When P(S|R) > P(S|A), revolution is rational.

ContradictionSystem
-------------------

:py:class:`babylon.engine.systems.contradiction.ContradictionSystem`

**Purpose:** Accumulate tension from class contradictions.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Class attributes, contradiction definitions
   * - **Outputs**
     - Updated tension values, potential rupture flags

**Logic:**

.. code-block:: python

   for contradiction in active_contradictions:
       tension_delta = calculate_tension_increase(contradiction, graph)
       graph.nodes[node]["tension"] += tension_delta

       if graph.nodes[node]["tension"] > rupture_threshold:
           flag_potential_rupture(node, graph)

TerritorySystem
---------------

:py:class:`babylon.engine.systems.territory.TerritorySystem`

**Purpose:** Process territorial heat, eviction, and displacement.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Territory heat, operational profiles, TENANCY edges
   * - **Outputs**
     - Updated heat, displaced classes, detention states

**Logic:**

.. code-block:: python

   for territory in territories:
       # Decay heat
       territory["heat"] *= (1 - heat_decay)

       # Add heat from activities
       territory["heat"] += calculate_activity_heat(territory)

       # Trigger eviction if above threshold
       if territory["heat"] >= heat_threshold:
           evict_classes(territory, graph)

**Operational profiles:**

- ``HIGH_PROFILE``: Visible activity, generates heat
- ``LOW_PROFILE``: Covert activity, heat decays naturally

StruggleSystem
--------------

:py:class:`babylon.engine.systems.struggle.StruggleSystem`

**Purpose:** Implement agency responses to state action.

.. list-table::
   :widths: 20 80

   * - **Inputs**
     - Repression events, organization levels
   * - **Outputs**
     - Uprising events, changed class states

**Logic:**

.. code-block:: python

   # When state uses EXCESSIVE_FORCE
   if excessive_force_event:
       affected_class = event.target

       # High organization + excessive force = uprising
       if graph.nodes[affected_class]["organization"] > uprising_threshold:
           trigger_uprising(affected_class, graph)
           services.event_bus.emit(UprisingEvent(class_id=affected_class))

**Key insight:** Repression can backfire when directed at organized classes.

See Also
--------

- :doc:`/concepts/simulation-systems` - Why systems work this way
- :doc:`/how-to/add-custom-system` - Create custom systems
- :doc:`configuration` - System parameters (GameDefines)
- :py:mod:`babylon.engine.systems` - Source code
