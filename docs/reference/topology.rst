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
~~~~~~~~~~~~~~~

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

.. py:method:: _classify_phase(percolation_ratio)

   Classify current phase state from percolation ratio.

   :param percolation_ratio: Current L_max / N ratio
   :type percolation_ratio: float
   :returns: Phase state name
   :rtype: str ("gaseous" | "transitional" | "liquid")

.. py:method:: get_pending_events()

   Return and clear pending events list.

   :returns: List of events awaiting injection
   :rtype: list[SimulationEvent]

**Phase States:**

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

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
     - ``ratio >= 0.5``
     - Giant component formed, vanguard crystallized

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
   * - Condensation
     - ``percolation_ratio`` crosses 0.5
     - "Vanguard Party has formed"
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
- :py:mod:`babylon.systems.formulas` - Mathematical formulas
