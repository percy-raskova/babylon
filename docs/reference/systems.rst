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

**Purpose:** Implement the 5-phase Imperial Circuit with pool-based resource tracking.

The Imperial Circuit (Sprint 3.4.1, 3.4.4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Imperial Circuit models MLM-TW value extraction as a 5-phase cycle with
finite resources tracked via an ``imperial_rent_pool`` ("The Gas Tank"):

.. code-block:: text

   Phase 1: EXPLOITATION     Phase 2: TRIBUTE        Phase 3: WAGES
   P_w ──────────► P_c ──────────► C_b ──────────► C_w
   (Periphery      (Comprador      (Core           (Labor
    Worker)         Class)          Bourgeoisie)    Aristocracy)
        │               │               │
        │               │               ▼
        │               │          DRAINS POOL
        │               │
        │               ▼
        │          FEEDS POOL
        │
        └──────────────────────────────────────────────┐
                                                       │
   Phase 4: CLIENT_STATE (Iron Lung)                   │
   C_b ──────────► P_c                                 │
        │          (converts to repression)            │
        ▼                                              │
   DRAINS POOL                                         │
                                                       │
   Phase 5: DECISION ◄─────────────────────────────────┘
   (Bourgeoisie heuristics adjust wage_rate/repression)

**Phase Summary:**

.. list-table::
   :header-rows: 1
   :widths: 10 15 30 20 25

   * - Phase
     - Edge Type
     - Description
     - Pool Effect
     - Formula
   * - 1
     - EXPLOITATION
     - Extract imperial rent from periphery workers
     - (direct to C_b feeds pool)
     - :math:`\Phi = \alpha W_p (1 - \Psi_p)`
   * - 2
     - TRIBUTE
     - Comprador sends 85% to core (keeps 15% cut)
     - **FEEDS** pool
     - ``tribute = wealth * (1 - comprador_cut)``
   * - 3
     - WAGES
     - Super-wages to labor aristocracy
     - **DRAINS** pool
     - ``wages = tribute_inflow * wage_rate``
   * - 4
     - CLIENT_STATE
     - Subsidy converts to repression capacity
     - **DRAINS** pool
     - Triggered when :math:`P(S|R) \geq \theta \cdot P(S|A)`
   * - 5
     - (internal)
     - Bourgeoisie decision heuristics
     - Adjusts rates
     - See Decision Matrix below

The PPP Model (Super-Wages)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Super-wages don't manifest as direct cash transfers. Instead, the labor
aristocracy receives nominal wages but enjoys enhanced purchasing power
due to cheap commodities from the periphery. This is **Purchasing Power Parity**:

.. math::

   \text{PPP Multiplier} = 1 + (\alpha \times m_{superwage} \times p_{impact})

.. math::

   \text{Effective Wealth} = W_{nominal} + W_{nominal} \times (\text{PPP Mult} - 1)

.. math::

   \text{Unearned Increment} = \text{Effective Wealth} - W_{nominal}

The "unearned increment" is the material basis of labor aristocracy loyalty -
they receive more than they produce via imperial rent transfer.

The Iron Lung (Client State Subsidy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a client state becomes unstable (:math:`P(S|R) \geq \theta \times P(S|A)`),
the core provides subsidy that **converts to repression capacity**, not wealth.
This models military aid, police training, and suppression infrastructure.

Wealth is NOT conserved - it transforms into suppression capability:

.. code-block:: python

   repression_boost = subsidy_amount * conversion_rate
   target["repression_faced"] = min(1.0, current + repression_boost)

Decision Heuristics (Phase 5)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Based on ``pool_ratio`` and ``aggregate_tension``, the bourgeoisie chooses:

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 20 20

   * - Decision
     - Pool Ratio
     - Tension
     - Wage Delta
     - Repression Delta
   * - **BRIBERY**
     - ≥ 0.7
     - < 0.3
     - +5%
     - 0
   * - **NO_CHANGE**
     - 0.3-0.7
     - any
     - 0
     - 0
   * - **AUSTERITY**
     - < 0.3
     - ≤ 0.5
     - -5%
     - 0
   * - **IRON_FIST**
     - < 0.3
     - > 0.5
     - 0
     - +10%
   * - **CRISIS**
     - < 0.1
     - any
     - -15%
     - +20%

**Events Emitted:**

- ``SURPLUS_EXTRACTION``: On each rent extraction (Phase 1)
- ``IMPERIAL_SUBSIDY``: On client state subsidy (Phase 4)
- ``ECONOMIC_CRISIS``: When CRISIS decision triggers (Phase 5)

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
