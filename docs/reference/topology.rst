Topology System Reference
=========================

This reference documents the topology monitoring system that tracks revolutionary
organization via percolation theory. For conceptual background, see
:doc:`/concepts/percolation-theory`.

Overview
--------

The topology system analyzes the solidarity subgraph to detect phase transitions
in organizational structure. It is implemented as a :class:`SimulationObserver`
that receives state change notifications and computes topological metrics.

**Key Components:**

- :py:mod:`babylon.engine.topology_monitor` - Observer and helper functions
- :py:mod:`babylon.models.topology_metrics` - Data models for metrics

Constants & Thresholds
----------------------

Phase Detection
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Constant
     - Value
     - Purpose
   * - ``GASEOUS_THRESHOLD``
     - 0.1
     - Percolation ratio below this indicates atomized movement
   * - ``CONDENSATION_THRESHOLD``
     - 0.5
     - Crossing this threshold triggers phase shift detection
   * - ``BRITTLE_MULTIPLIER``
     - 2
     - If potential > actual × this, movement is brittle

Liquidity Classification
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Constant
     - Value
     - Purpose
   * - ``POTENTIAL_MIN_STRENGTH``
     - 0.1
     - Minimum solidarity strength for sympathizer classification
   * - ``ACTUAL_MIN_STRENGTH``
     - 0.5
     - Minimum solidarity strength for cadre classification

Resilience Testing
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Constant
     - Value
     - Purpose
   * - ``DEFAULT_REMOVAL_RATE``
     - 0.2
     - Fraction of nodes removed in purge simulation (20%)
   * - ``DEFAULT_SURVIVAL_THRESHOLD``
     - 0.4
     - Giant component must survive at 40% of original size

Metrics
-------

TopologySnapshot
~~~~~~~~~~~~~~~~

The :class:`TopologySnapshot` model captures metrics at each tick:

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``tick``
     - ``int``
     - Simulation tick number
   * - ``num_components``
     - ``int``
     - Number of disconnected solidarity cells
   * - ``max_component_size``
     - ``int``
     - Size of largest connected component (L_max)
   * - ``total_nodes``
     - ``int``
     - Total social_class nodes in system
   * - ``percolation_ratio``
     - ``Probability``
     - L_max / total_nodes (range [0, 1])
   * - ``potential_liquidity``
     - ``int``
     - Count of SOLIDARITY edges > 0.1 strength
   * - ``actual_liquidity``
     - ``int``
     - Count of SOLIDARITY edges > 0.5 strength
   * - ``cadre_density``
     - ``float``
     - actual/potential liquidity ratio [0, 1] (Sprint 3.3)
   * - ``is_resilient``
     - ``bool | None``
     - Whether network survives purge test (None if not tested)

ResilienceResult
~~~~~~~~~~~~~~~~

The :class:`ResilienceResult` model captures purge simulation output:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Field
     - Type
     - Description
   * - ``is_resilient``
     - ``bool``
     - True if network survives simulated purge
   * - ``original_max_component``
     - ``int``
     - L_max before node removal
   * - ``post_purge_max_component``
     - ``int``
     - L_max after removing nodes
   * - ``removal_rate``
     - ``float``
     - Fraction of nodes removed
   * - ``survival_threshold``
     - ``float``
     - Required survival fraction
   * - ``seed``
     - ``int | None``
     - RNG seed for reproducibility

Functions
---------

extract_solidarity_subgraph
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: extract_solidarity_subgraph(G, min_strength=0.0)

   Extract undirected solidarity network from WorldState graph.

   :param G: Directed graph from ``WorldState.to_graph()``
   :type G: nx.DiGraph[str]
   :param min_strength: Minimum solidarity_strength to include edge
   :type min_strength: float
   :returns: Undirected graph with only SOLIDARITY edges above threshold
   :rtype: nx.Graph[str]

   **Example:**

   .. code-block:: python

      from babylon.engine.topology_monitor import extract_solidarity_subgraph

      graph = state.to_graph()
      solidarity_graph = extract_solidarity_subgraph(graph, min_strength=0.1)

calculate_component_metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: calculate_component_metrics(solidarity_graph, total_social_classes)

   Calculate connected component metrics for percolation analysis.

   :param solidarity_graph: Undirected solidarity graph
   :type solidarity_graph: nx.Graph[str]
   :param total_social_classes: Total number of social_class nodes
   :type total_social_classes: int
   :returns: Tuple of (num_components, max_component_size, percolation_ratio)
   :rtype: tuple[int, int, float]

   **Example:**

   .. code-block:: python

      from babylon.engine.topology_monitor import (
          extract_solidarity_subgraph,
          calculate_component_metrics,
      )

      solidarity_graph = extract_solidarity_subgraph(graph)
      num_comp, l_max, ratio = calculate_component_metrics(
          solidarity_graph, total_social_classes=20
      )

calculate_liquidity
~~~~~~~~~~~~~~~~~~~

.. py:function:: calculate_liquidity(G)

   Calculate potential vs actual solidarity metrics.

   :param G: Directed graph from ``WorldState.to_graph()``
   :type G: nx.DiGraph[str]
   :returns: Tuple of (potential_liquidity, actual_liquidity)
   :rtype: tuple[int, int]

   **Interpretation:**

   - ``potential``: Sympathizer network (edges > 0.1)
   - ``actual``: Cadre network (edges > 0.5)
   - If ``potential > actual * 2``: Movement is broad but brittle

check_resilience
~~~~~~~~~~~~~~~~

.. py:function:: check_resilience(G, removal_rate=0.2, survival_threshold=0.4, seed=None)

   Test if solidarity network survives targeted node removal.

   Simulates a "purge" scenario by removing a percentage of nodes and
   checking if the giant component survives.

   :param G: Directed graph from ``WorldState.to_graph()``
   :type G: nx.DiGraph[str]
   :param removal_rate: Fraction of nodes to remove (default 0.2)
   :type removal_rate: float
   :param survival_threshold: Required survival fraction (default 0.4)
   :type survival_threshold: float
   :param seed: RNG seed for reproducibility
   :type seed: int | None
   :returns: Result with is_resilient flag and metrics
   :rtype: ResilienceResult

   **Example:**

   .. code-block:: python

      from babylon.engine.topology_monitor import check_resilience

      result = check_resilience(graph, removal_rate=0.2, seed=42)
      if not result.is_resilient:
          print("Sword of Damocles: Network is fragile!")

TopologyMonitor Class
---------------------

.. py:class:: TopologyMonitor(resilience_test_interval=5, resilience_removal_rate=0.2, logger=None)

   Observer tracking solidarity network condensation via percolation theory.

   Implements :class:`SimulationObserver` protocol.

   :param resilience_test_interval: Run resilience test every N ticks (0 = disabled)
   :type resilience_test_interval: int
   :param resilience_removal_rate: Fraction of nodes to remove in test
   :type resilience_removal_rate: float
   :param logger: Logger instance (default: module logger)
   :type logger: logging.Logger | None

Configuration
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - ``resilience_test_interval``
     - 5
     - Test resilience every N ticks (0 disables)
   * - ``resilience_removal_rate``
     - 0.2
     - Fraction of nodes removed in purge test

Properties
~~~~~~~~~~

.. py:attribute:: name
   :type: str

   Returns ``"TopologyMonitor"``

.. py:attribute:: history
   :type: list[TopologySnapshot]

   Returns copy of recorded snapshots (one per tick)

Lifecycle Hooks
~~~~~~~~~~~~~~~

.. py:method:: on_simulation_start(initial_state, config)

   Called when simulation begins. Clears history and records initial snapshot.

.. py:method:: on_tick(previous_state, new_state)

   Called after each tick. Records snapshot and logs narrative states.

.. py:method:: on_simulation_end(final_state)

   Called when simulation ends. Logs summary statistics.

Event Emission (Sprint 3.3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TopologyMonitor emits :class:`PhaseTransitionEvent` when percolation ratio
crosses threshold boundaries. Events are collected and injected into the next
tick's WorldState.

**Internal State:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Attribute
     - Type
     - Description
   * - ``_previous_phase``
     - ``str | None``
     - Last known phase state
   * - ``_pending_events``
     - ``list[SimulationEvent]``
     - Events awaiting collection

**Methods:**

.. py:method:: _classify_phase(percolation_ratio, cadre_density=0.0)

   Classify current phase state from percolation ratio and cadre density.

   :param percolation_ratio: Current L_max / N ratio
   :type percolation_ratio: float
   :param cadre_density: Ratio of actual/potential liquidity (default 0.0)
   :type cadre_density: float
   :returns: Phase state name
   :rtype: str ("gaseous" | "transitional" | "liquid" | "solid")

.. py:method:: get_pending_events()

   Return and clear pending events list.

   :returns: List of events awaiting injection
   :rtype: list[SimulationEvent]

**Phase States (4-Phase Model - Sprint 3.3):**

.. list-table::
   :header-rows: 1
   :widths: 15 35 50

   * - State
     - Threshold
     - Political Meaning
   * - Gaseous
     - ``ratio < 0.1``
     - Atomized leftism, no coordination capacity
   * - Transitional
     - ``0.1 <= ratio < 0.5``
     - Emerging structure, vulnerable to disruption
   * - Liquid
     - ``ratio >= 0.5 AND cadre < 0.5``
     - Mass movement formed, broad but lacks discipline
   * - Solid
     - ``ratio >= 0.5 AND cadre >= 0.5``
     - Vanguard party crystallized, iron discipline

Narrative States
~~~~~~~~~~~~~~~~

The monitor logs these narrative states based on metrics:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - State
     - Condition
     - Log Message
   * - Gaseous
     - ``percolation_ratio < 0.1``
     - "Movement is atomized"
   * - Liquid
     - ``ratio >= 0.5 AND cadre < 0.5``
     - "Mass movement formed, lacks cadre discipline"
   * - Solid
     - ``ratio >= 0.5 AND cadre >= 0.5``
     - "Vanguard Party crystallized, iron discipline"
   * - Crystallization
     - ``liquid -> solid`` transition
     - "Mass movement hardened into disciplined vanguard"
   * - Brittle
     - ``potential > actual * 2``
     - "Movement is broad but brittle"
   * - Sword of Damocles
     - ``is_resilient == False``
     - "A purge would destroy the movement"

Usage Example
-------------

.. code-block:: python

   from babylon.engine.simulation import Simulation
   from babylon.engine.topology_monitor import TopologyMonitor
   from babylon.models import WorldState, SimulationConfig

   # Create initial state
   state = WorldState(entities={...}, relationships=[...])
   config = SimulationConfig()

   # Create monitor
   monitor = TopologyMonitor(resilience_test_interval=5)

   # Create simulation with observer
   sim = Simulation(state, config, observers=[monitor])

   # Run simulation
   for _ in range(10):
       sim.step()

   # Access metrics
   for snapshot in monitor.history:
       print(f"Tick {snapshot.tick}: p={snapshot.percolation_ratio:.2f}")

   sim.end()

See Also
--------

- :doc:`/concepts/percolation-theory` - Conceptual explanation of percolation theory
- :doc:`/concepts/event-system` - Event system architecture
- :doc:`/reference/events` - Complete event type reference (includes PhaseTransitionEvent)
- :doc:`/concepts/imperial-rent` - Related economic mechanics
- :py:mod:`babylon.engine.systems.solidarity` - Solidarity transmission system
- :py:mod:`babylon.formulas` - Mathematical formulas


.. _bifurcation-analysis-reference:

Bifurcation Topology Analysis
==============================

Consciousness-weighted analysis predicting whether crisis routes to fascism
or revolution. For conceptual background, see
:doc:`/concepts/george-jackson-model`.

**Key Modules:**

- :py:mod:`babylon.domain.bifurcation` - Package with all analysis functions
- :py:mod:`babylon.domain.bifurcation.analysis` - Full orchestrator
- :py:mod:`babylon.domain.bifurcation.consciousness` - Sigmoid weighting
- :py:mod:`babylon.domain.bifurcation.axis` - Per-axis contradiction analysis
- :py:mod:`babylon.domain.bifurcation.bridges` - Community bridge detection
- :py:mod:`babylon.domain.bifurcation.resilience` - Topological resilience metrics
- :py:mod:`babylon.domain.bifurcation.ceiling` - Material solidarity ceiling
- :py:mod:`babylon.domain.bifurcation.legitimation` - Legitimation crisis amplifier
- :py:mod:`babylon.domain.bifurcation.types` - Result types
- :py:mod:`babylon.engine.bifurcation_monitor` - Tick-level observer
- :py:mod:`babylon.engine.community_state_store` - Community state protocol

BifurcationDefines
------------------

Configurable parameters in ``GameDefines.bifurcation``.

Consciousness Sigmoid (US1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``consciousness_sigmoid_midpoint``
     - 0.4
     - CI value at sigmoid inflection. Below-center so breakage cliff catches assimilated communities.
   * - ``consciousness_sigmoid_steepness``
     - 10.0
     - Slope at inflection point. Higher values produce a sharper cliff.
   * - ``consciousness_filter_threshold``
     - 0.2
     - Minimum sigmoid output to include edge in filtered subgraph.

Classification (US5)
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``indeterminate_dead_zone``
     - 0.2
     - Score within +/-0.2 of 1.0 threshold classifies as "indeterminate".
   * - ``axis_tendency_epsilon``
     - 0.001
     - Division guard for cross-solidarity / lateral-antagonism ratio.

Legitimation Amplifier (US7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``legitimation_amplifier_scale``
     - 2.0
     - At zero legitimation, crisis intensity multiplied by this factor.

Solidarity Ceiling (US6)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``wage_ceiling_high_ratio``
     - 10.0
     - Wage gap ratio at which ceiling reaches its minimum.
   * - ``wage_ceiling_low_ratio``
     - 2.0
     - Wage gap ratio at which ceiling reaches its maximum.
   * - ``wage_ceiling_min``
     - 0.3
     - Minimum solidarity ceiling (at extreme wage gaps).
   * - ``wage_ceiling_max``
     - 0.9
     - Maximum solidarity ceiling (at similar wages).
   * - ``shared_exploitation_bonus``
     - 0.2
     - Ceiling bonus when agents share an exploitation source.

Purge Resilience (US4)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``purge_removal_rate``
     - 0.2
     - Fraction of high-degree nodes removed in purge resilience test.

Result Types
------------

BifurcationResult
~~~~~~~~~~~~~~~~~

Frozen Pydantic model produced by :func:`~babylon.domain.bifurcation.analysis.bifurcation_tendency`.
One instance per analysis call.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Type
     - Description
   * - ``overall_tendency``
     - ``Literal``
     - ``"revolutionary"``, ``"fascist"``, or ``"indeterminate"``
   * - ``per_axis_tendency``
     - ``dict[str, float]``
     - Axis ID to tendency ratio (all axes, including inactive)
   * - ``cross_line_solidarity_count``
     - ``int``
     - Raw SOLIDARITY edges crossing any contradiction axis
   * - ``within_line_solidarity_count``
     - ``int``
     - Raw SOLIDARITY edges within the same side of an axis
   * - ``lateral_antagonism_count``
     - ``int``
     - Antagonistic edges within same side (lateral conflict)
   * - ``upward_antagonism_count``
     - ``int``
     - Antagonistic edges from marginalized toward hegemonic
   * - ``consciousness_weighted_cross_solidarity``
     - ``float``
     - Sum of consciousness-weighted cross-line solidarity values
   * - ``mean_collective_identity_marginalized``
     - ``float``
     - Mean CI across marginalized communities [0, 1]
   * - ``dominant_tendency_distribution``
     - ``dict[str, float]``
     - ConsciousnessTendency fractions across marginalized communities
   * - ``community_bridge_count``
     - ``int``
     - Number of communities spanning contradiction axes
   * - ``bridge_potential_weighted``
     - ``float``
     - Sum of infrastructure * sigmoid(CI) for bridge communities
   * - ``legitimation_index``
     - ``float``
     - Population-weighted mean legitimation [0, 1]
   * - ``raw_beta_0``
     - ``int``
     - Connected components (all SOLIDARITY edges)
   * - ``raw_beta_1``
     - ``int``
     - Cycle rank (all SOLIDARITY edges)
   * - ``filtered_beta_0``
     - ``int``
     - Connected components (consciousness-filtered edges only)
   * - ``filtered_beta_1``
     - ``int``
     - Cycle rank (consciousness-filtered edges only)
   * - ``resilience_under_targeted_purge``
     - ``float``
     - Post-purge L_max / pre-purge L_max on filtered subgraph [0, 1]
   * - ``equivalence_class_distribution``
     - ``dict[int, int]``
     - Maps class size to count of structurally equivalent groups
   * - ``critical_singletons``
     - ``list[str]``
     - Articulation point node IDs on filtered subgraph
   * - ``critical_cutsets``
     - ``list[frozenset[str]]``
     - Minimum edge cuts on filtered subgraph (bounded by max_cutset_size=3)
   * - ``mean_assimilation_ratio_marginalized``
     - ``float``
     - Mean ``f / (l + f)`` across marginalized communities [0, 1]. Default: 0.0. (Feature 034)
   * - ``crisis_fragile_edge_count``
     - ``int``
     - Solidarity edges where effective CI < 0.3 (crisis-fragile). Default: 0. (Feature 034)

BifurcationSnapshot
~~~~~~~~~~~~~~~~~~~

Wraps :class:`~babylon.domain.bifurcation.types.BifurcationResult` with tick metadata.
Stored in ``BifurcationMonitor._bifurcation_history``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Field
     - Type
     - Description
   * - ``tick``
     - ``int``
     - Simulation tick when computed (>= 0)
   * - ``result``
     - ``BifurcationResult``
     - Full analysis result for this tick

AxisTendency
~~~~~~~~~~~~

Per-contradiction-axis analysis result.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Type
     - Description
   * - ``axis_id``
     - ``str``
     - Matches ``ContradictionAxis.id`` (e.g. ``"colonial"``, ``"patriarchal"``)
   * - ``cross_solidarity_weighted``
     - ``float``
     - Sum of consciousness-weighted cross-line solidarity (>= 0)
   * - ``lateral_antagonism_weighted``
     - ``float``
     - Sum of antagonistic edge weights on same side (>= 0)
   * - ``tendency_ratio``
     - ``float``
     - cross / (lateral + epsilon); > 1.0 = solidarity-dominant
   * - ``cross_edge_count``
     - ``int``
     - Raw count of cross-line solidarity edges
   * - ``lateral_edge_count``
     - ``int``
     - Raw count of lateral antagonism edges
   * - ``upward_edge_count``
     - ``int``
     - Raw count of upward antagonism edges

BridgeInfo
~~~~~~~~~~

Community spanning a contradiction axis with weighted potential.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``community_type``
     - ``CommunityType``
     - Which community (e.g. ``DISABLED``, ``INCARCERATED``)
   * - ``axes_spanned``
     - ``list[str]``
     - ContradictionAxis IDs this community bridges (min length 1)
   * - ``collective_identity``
     - ``float``
     - Raw CI from CommunityConsciousness [0, 1]
   * - ``sigmoid_ci``
     - ``float``
     - Sigmoid-transformed CI [0, 1]
   * - ``infrastructure``
     - ``float``
     - Community infrastructure from CommunityState [0, 1]
   * - ``weighted_potential``
     - ``float``
     - infrastructure * sigmoid_ci
   * - ``member_count``
     - ``int``
     - Number of agents in this community

SolidarityCeiling
~~~~~~~~~~~~~~~~~

Material constraints on solidarity between two agents.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``base_ceiling``
     - ``float``
     - From wage gap ratio interpolation [0, 1]
   * - ``exploitation_bonus``
     - ``float``
     - +0.2 if shared exploitation source [0, 0.2]
   * - ``community_bonus``
     - ``float``
     - Bonus from shared community membership (>= 0)
   * - ``effective_ceiling``
     - ``float``
     - Clamped sum of all components [0, 1]
   * - ``wage_gap_ratio``
     - ``float``
     - max(w_a, w_b) / min(w_a, w_b)
   * - ``geographically_proximate``
     - ``bool``
     - Whether agents share ADJACENCY-linked territories

Analysis Functions
------------------

bifurcation_tendency
~~~~~~~~~~~~~~~~~~~~

.. py:function:: bifurcation_tendency(graph, H, community_states, agent_memberships, defines)

   Compute full bifurcation analysis.

   Combines per-axis contradiction tendency (weakest-link), community bridge
   potential (consciousness-weighted), legitimation crisis amplifier, and
   topological resilience (two-pass Betti numbers).

   :param graph: Simulation DiGraph with ``social_class`` and ``territory`` nodes
   :type graph: nx.DiGraph
   :param H: XGI hypergraph for community membership lookup
   :type H: xgi.Hypergraph
   :param community_states: Community consciousness data
   :type community_states: dict[CommunityType, CommunityState]
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :param defines: Configurable parameters
   :type defines: BifurcationDefines
   :returns: Frozen result with all analysis fields populated
   :rtype: BifurcationResult

   **Example:**

   .. code-block:: python

      from babylon.domain.bifurcation import bifurcation_tendency
      from babylon.config.defines import BifurcationDefines

      result = bifurcation_tendency(
          graph=sim_graph,
          H=hypergraph,
          community_states=states,
          agent_memberships=memberships,
          defines=BifurcationDefines(),
      )
      print(result.overall_tendency)  # "revolutionary", "fascist", or "indeterminate"

consciousness_sigmoid
~~~~~~~~~~~~~~~~~~~~~

.. py:function:: consciousness_sigmoid(collective_identity, midpoint, steepness)

   Nonlinear transform with breakage cliff for consciousness weighting.

   Logistic sigmoid: ``1 / (1 + exp(-steepness * (ci - midpoint)))``.
   Exponent clamped to [-500, +500] to prevent overflow.

   :param collective_identity: Raw CI value [0, 1]
   :type collective_identity: float
   :param midpoint: Sigmoid inflection point
   :type midpoint: float
   :param steepness: Slope at inflection
   :type steepness: float
   :returns: Transformed value [0, 1]. Near-zero below midpoint, near-one above.
   :rtype: float

WeightedSolidarityResult
~~~~~~~~~~~~~~~~~~~~~~~~

Result of consciousness-weighted solidarity computation (Feature 034).
Extends the original float return with a crisis-fragile marker.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``weight``
     - ``float``
     - Consciousness-weighted solidarity value (>= 0)
   * - ``crisis_fragile``
     - ``bool``
     - ``True`` if effective CI < crisis-fragile threshold (0.3). Default: ``False``.

Defined in :py:class:`~babylon.domain.bifurcation.types.WeightedSolidarityResult`.
See :doc:`/reference/ternary-consciousness` for full details.

consciousness_weighted_solidarity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: consciousness_weighted_solidarity(source_id, target_id, graph, H, community_states, defines)

   Weight a solidarity edge by consciousness of connected communities.

   For each agent, finds marginalized community memberships via the hypergraph,
   computes mean CI, then weights the edge by ``sigmoid(min(source_ci, target_ci))``.

   Edges where the effective CI (min of both endpoints) falls below the
   crisis-fragile threshold (0.3) are marked as crisis-fragile (Feature 034).

   :param source_id: Source agent node ID
   :type source_id: str
   :param target_id: Target agent node ID
   :type target_id: str
   :param graph: The simulation DiGraph (for edge attribute access)
   :type graph: nx.DiGraph
   :param H: XGI hypergraph (for community membership lookup)
   :type H: xgi.Hypergraph
   :param community_states: Current community consciousness data
   :type community_states: dict[CommunityType, CommunityState]
   :param defines: Configurable parameters (sigmoid midpoint/steepness)
   :type defines: BifurcationDefines
   :returns: Weighted solidarity with crisis-fragile flag
   :rtype: WeightedSolidarityResult

crosses_contradiction_axis
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: crosses_contradiction_axis(source_id, target_id, axis, agent_memberships)

   Check if an edge crosses the given contradiction axis.

   An edge crosses when one endpoint is on the hegemonic side and the other
   is on the marginalized side.

   :param source_id: Source agent node ID
   :type source_id: str
   :param target_id: Target agent node ID
   :type target_id: str
   :param axis: The contradiction axis to check
   :type axis: ContradictionAxis
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :returns: True if the edge spans hegemonic and marginalized sides
   :rtype: bool

classify_edge_antagonism
~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: classify_edge_antagonism(source_id, target_id, graph, axis, agent_memberships)

   Classify antagonistic direction of an edge along a contradiction axis.

   Only EXPLOITATION, REPRESSION, and COMPETITION edges are classified.

   :param source_id: Source agent node ID
   :type source_id: str
   :param target_id: Target agent node ID
   :type target_id: str
   :param graph: The simulation DiGraph
   :type graph: nx.DiGraph
   :param axis: The contradiction axis to classify against
   :type axis: ContradictionAxis
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :returns: ``"lateral"`` (same side), ``"upward"`` (marginalized toward hegemonic), ``"downward"`` (hegemonic toward marginalized), or ``"none"``
   :rtype: str

compute_axis_tendency
~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_axis_tendency(graph, H, axis, community_states, agent_memberships, defines)

   Compute solidarity vs antagonism balance along a single contradiction axis.

   Sums consciousness-weighted cross-line solidarity and lateral antagonism.
   Returns ``tendency_ratio = cross / (lateral + epsilon)``.

   :param graph: The simulation DiGraph
   :type graph: nx.DiGraph
   :param H: XGI hypergraph for community membership lookup
   :type H: xgi.Hypergraph
   :param axis: The contradiction axis to analyze
   :type axis: ContradictionAxis
   :param community_states: Current community consciousness data
   :type community_states: dict[CommunityType, CommunityState]
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :param defines: Configurable parameters
   :type defines: BifurcationDefines
   :returns: AxisTendency with all counts and weighted totals
   :rtype: AxisTendency

detect_bridges
~~~~~~~~~~~~~~

.. py:function:: detect_bridges(H, community_states, axes, agent_memberships, defines)

   Detect communities spanning contradiction axes, weighted by consciousness.

   Iterates INSTITUTIONAL_EXCLUSION communities in the hypergraph. For each,
   checks if members span both sides of any contradiction axis. Returns
   weighted bridge potential = infrastructure * sigmoid(CI).

   :param H: XGI hypergraph with communities as hyperedges
   :type H: xgi.Hypergraph
   :param community_states: Current community consciousness and infrastructure
   :type community_states: dict[CommunityType, CommunityState]
   :param axes: Contradiction axes to check spanning against
   :type axes: list[ContradictionAxis]
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :param defines: Configurable parameters (sigmoid midpoint/steepness)
   :type defines: BifurcationDefines
   :returns: List of BridgeInfo for each community spanning at least one axis
   :rtype: list[BridgeInfo]

compute_solidarity_ceiling
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_solidarity_ceiling(node_a_id, node_b_id, graph, agent_memberships, defines)

   Compute material solidarity ceiling between two agents.

   The ceiling is the maximum achievable solidarity given material conditions
   (wage gap, shared exploitation, shared community membership, geography).

   :param node_a_id: First agent node ID
   :type node_a_id: str
   :param node_b_id: Second agent node ID
   :type node_b_id: str
   :param graph: Simulation graph with wealth and edge attributes
   :type graph: nx.DiGraph
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :param defines: Bifurcation coefficient configuration
   :type defines: BifurcationDefines
   :returns: SolidarityCeiling with all computed components
   :rtype: SolidarityCeiling

compute_legitimation_amplifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_legitimation_amplifier(graph, defines)

   Compute crisis amplifier from population-weighted mean legitimation.

   :param graph: Simulation graph with territory nodes carrying ``legitimation_index`` and ``population``
   :type graph: nx.DiGraph
   :param defines: Provides ``legitimation_amplifier_scale``
   :type defines: BifurcationDefines
   :returns: Crisis amplifier in [1.0, legitimation_amplifier_scale]. Returns 1.0 if no territories.
   :rtype: float

Resilience Functions
--------------------

compute_betti_numbers
~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_betti_numbers(subgraph)

   Compute Betti numbers for an undirected graph.

   :param subgraph: Undirected solidarity subgraph
   :type subgraph: nx.Graph
   :returns: Tuple of (beta_0, beta_1) where beta_0 = connected components, beta_1 = |E| - |V| + beta_0
   :rtype: tuple[int, int]

compute_equivalence_classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_equivalence_classes(subgraph)

   Group nodes by structural equivalence (identical neighbor sets).

   :param subgraph: Undirected solidarity subgraph
   :type subgraph: nx.Graph
   :returns: Maps class_size to count of classes with that size
   :rtype: dict[int, int]

find_critical_singletons
~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: find_critical_singletons(subgraph)

   Find articulation points whose removal disconnects the graph.

   :param subgraph: Undirected solidarity subgraph
   :type subgraph: nx.Graph
   :returns: Sorted list of node IDs that are articulation points
   :rtype: list[str]

find_critical_cutsets
~~~~~~~~~~~~~~~~~~~~~

.. py:function:: find_critical_cutsets(subgraph, max_cutset_size=3)

   Find minimum edge cuts per connected component, bounded by size.

   :param subgraph: Undirected solidarity subgraph
   :type subgraph: nx.Graph
   :param max_cutset_size: Maximum cut size to include (default 3)
   :type max_cutset_size: int
   :returns: List of frozensets, each containing node IDs in the minimum edge cut
   :rtype: list[frozenset[str]]

compute_purge_resilience
~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: compute_purge_resilience(subgraph, removal_rate, seed=None)

   Measure resilience to targeted removal of high-degree nodes.

   Removes top-degree nodes at the given rate and compares post-purge to
   pre-purge largest component size.

   :param subgraph: Undirected solidarity subgraph
   :type subgraph: nx.Graph
   :param removal_rate: Fraction of nodes to remove [0, 1]
   :type removal_rate: float
   :param seed: RNG seed for tie-breaking (default None)
   :type seed: int | None
   :returns: Post-purge L_max / pre-purge L_max, clamped to [0, 1]. Returns 1.0 for empty graphs.
   :rtype: float

BifurcationMonitor
------------------

.. py:class:: BifurcationMonitor(community_state_store, defines=None, logger=None)

   Monitor tracking bifurcation tendency across simulation ticks.

   Records :class:`~babylon.domain.bifurcation.types.BifurcationSnapshot` per tick
   and emits :class:`~babylon.models.events.BifurcationTendencyEvent` when
   the overall tendency changes.

   Accepts a :class:`~babylon.engine.community_state_store.CommunityStateStore`
   via dependency injection for community consciousness access.

   :param community_state_store: Protocol-based access to community states
   :type community_state_store: CommunityStateStore
   :param defines: Configurable bifurcation parameters (default: BifurcationDefines())
   :type defines: BifurcationDefines | None
   :param logger: Logger instance (default: module logger)
   :type logger: logging.Logger | None

Properties
~~~~~~~~~~

.. py:attribute:: bifurcation_history
   :type: list[BifurcationSnapshot]

   Returns copy of recorded bifurcation snapshots (one per tick).

Methods
~~~~~~~

.. py:method:: record_bifurcation(graph, H, agent_memberships, tick)

   Run bifurcation analysis and record snapshot.

   Calls :func:`~babylon.domain.bifurcation.analysis.bifurcation_tendency` with
   community states from the injected store, records the resulting
   :class:`~babylon.domain.bifurcation.types.BifurcationSnapshot`, and emits
   a :class:`~babylon.models.events.BifurcationTendencyEvent` if the
   overall tendency changed since the previous tick.

   :param graph: Simulation DiGraph with social_class and territory nodes
   :type graph: nx.DiGraph
   :param H: XGI hypergraph for community membership lookup
   :type H: xgi.Hypergraph
   :param agent_memberships: Agent ID to community memberships mapping
   :type agent_memberships: dict[str, set[CommunityType]]
   :param tick: Current simulation tick
   :type tick: int

.. py:method:: get_pending_events()

   Return and clear pending events. Same pattern as
   :meth:`TopologyMonitor.get_pending_events`.

   :returns: List of pending events (cleared after return)
   :rtype: list[SimulationEvent]

BifurcationTendencyEvent
~~~~~~~~~~~~~~~~~~~~~~~~

Emitted when ``overall_tendency`` changes between ticks. Inherits
:class:`~babylon.models.events.TopologyEvent`.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``BIFURCATION_TENDENCY_CHANGE``
   * - ``percolation_ratio``
     - ``float``
     - Set to 0.0 (not tracked by bifurcation monitor)
   * - ``num_components``
     - ``int``
     - ``filtered_beta_0`` from BifurcationResult
   * - ``previous_tendency``
     - ``str``
     - Overall tendency before change
   * - ``new_tendency``
     - ``str``
     - Overall tendency after change
   * - ``consciousness_weighted_cross_solidarity``
     - ``float``
     - Sum of consciousness-weighted cross-line solidarity
   * - ``mean_collective_identity_marginalized``
     - ``float``
     - Mean CI across marginalized communities
   * - ``bridge_potential_weighted``
     - ``float``
     - Sum of infrastructure * sigmoid(CI) for bridges
   * - ``legitimation_index``
     - ``float``
     - Population-weighted mean legitimation

CommunityStateStore Protocol
----------------------------

.. py:class:: CommunityStateStore

   Protocol for accessing community consciousness state. Enables dependency
   injection so ``BifurcationMonitor`` is decoupled from concrete state storage.

   .. py:method:: get_all()

      :returns: Mapping of community type to current community state
      :rtype: dict[CommunityType, CommunityState]

.. py:class:: InMemoryCommunityStateStore(states)

   Default implementation wrapping a dict.

   :param states: Initial community states
   :type states: dict[CommunityType, CommunityState]

Usage Example
~~~~~~~~~~~~~

.. code-block:: python

   from babylon.domain.bifurcation import bifurcation_tendency
   from babylon.config.defines import BifurcationDefines
   from babylon.engine.bifurcation_monitor import BifurcationMonitor
   from babylon.engine.community_state_store import InMemoryCommunityStateStore

   # Set up community state store
   store = InMemoryCommunityStateStore(community_states)

   # Create monitor
   monitor = BifurcationMonitor(
       community_state_store=store,
       defines=BifurcationDefines(),
   )

   # Record each tick
   monitor.record_bifurcation(
       graph=sim_graph,
       H=hypergraph,
       agent_memberships=memberships,
       tick=current_tick,
   )

   # Check for tendency changes
   events = monitor.get_pending_events()
   for event in events:
       print(f"Tendency changed: {event.previous_tendency} -> {event.new_tendency}")

   # Access history
   for snapshot in monitor.bifurcation_history:
       result = snapshot.result
       print(f"Tick {snapshot.tick}: {result.overall_tendency}")
