Percolation Theory & Phase Transitions
======================================

Babylon uses **percolation theory** from statistical physics to model
revolutionary phase transitions. The TopologyMonitor observes the
solidarity network, detecting when atomized movements "condense" into
organized revolutionary forces.

Theoretical Foundation
----------------------

Percolation theory studies how connected clusters form in networks.
Applied to revolutionary movements:

- **Sites** = Social classes (nodes)
- **Bonds** = SOLIDARITY edges
- **Percolation** = Giant component spans majority of network

When a network percolates, information (consciousness) can flow across
the entire system—the movement achieves coordination capacity.

Phase States
------------

The solidarity network exists in one of two phase states:

.. list-table:: Movement Phase States
   :header-rows: 1
   :widths: 20 40 40

   * - State
     - Network Property
     - Political Meaning
   * - **Gaseous**
     - Many small, disconnected components
     - Atomized leftism; no coordination
   * - **Liquid**
     - Giant component spans >50% of nodes
     - Vanguard Party formed; coordination possible

The Percolation Threshold
-------------------------

The **percolation threshold** (p_c) is the critical point where the
network transitions from gaseous to liquid:

.. math::

   p_c = \frac{L_{max}}{N} = 0.5

Where:

- :math:`L_{max}` = Size of largest connected component
- :math:`N` = Total number of social_class nodes

When the percolation ratio crosses 0.5, a **phase transition** occurs.

.. mermaid::

   xychart-beta
       title "Percolation Ratio Over Time"
       x-axis "Time (ticks)" [0, 10, 20, 30, 40, 50]
       y-axis "p(t)" 0 --> 1
       line [0.05, 0.15, 0.25, 0.40, 0.52, 0.75, 0.95]

The chart shows the phase transition: below 0.5 is GASEOUS (atomized),
above 0.5 is LIQUID (connected solidarity network).

Key Metrics
-----------

The TopologyMonitor tracks several metrics:

**num_components**
   Number of disconnected subgraphs. Higher = more atomized.

**max_component_size (L_max)**
   Size of the largest connected component—the organizational core.

**percolation_ratio**
   L_max / N. Below 0.5 = gaseous; above 0.5 = liquid.

**potential_liquidity**
   Count of SOLIDARITY edges > 0.1 strength (sympathizers).

**actual_liquidity**
   Count of SOLIDARITY edges > 0.5 strength (cadre).

The Liquidity Gap
-----------------

The ratio of potential to actual liquidity measures movement depth:

.. math::

   \text{Liquidity Gap} = \frac{\text{potential}}{\text{actual}}

.. list-table:: Liquidity Interpretation
   :header-rows: 1
   :widths: 30 70

   * - Gap Value
     - Interpretation
   * - Gap ≈ 1
     - Deep organization; sympathizers are committed
   * - Gap > 2
     - **Brittle movement**; broad but lacks discipline
   * - actual = 0
     - No cadre; purely sympathizer network

A brittle movement (high potential, low actual) is vulnerable to
targeted repression—removing key organizers collapses the network.

Resilience Testing: Sword of Damocles
-------------------------------------

The **Sword of Damocles** test simulates state repression:

1. Remove 20% of nodes (random purge)
2. Check if giant component survives at 40% of original size
3. If not, movement is **fragile**

.. code-block:: python

   def test_resilience(graph, removal_rate=0.2, survival_threshold=0.4):
       """Test if movement survives targeted purge."""
       original_L_max = get_max_component_size(graph)

       # Simulate purge
       purged = remove_random_nodes(graph.copy(), removal_rate)
       post_purge_L_max = get_max_component_size(purged)

       is_resilient = post_purge_L_max >= original_L_max * survival_threshold
       return ResilienceResult(
           is_resilient=is_resilient,
           original_max_component=original_L_max,
           post_purge_max_component=post_purge_L_max
       )

**Network Topology Matters:**

.. mermaid::

   flowchart TB
       subgraph STAR["STAR TOPOLOGY (Fragile)"]
           S0((Hub)) --- S1((●))
           S0 --- S2((●))
           S0 --- S3((●))
           S0 --- S4((●))
       end
       subgraph MESH["MESH TOPOLOGY (Resilient)"]
           M1((●)) --- M2((●)) --- M3((●))
           M4((●)) --- M5((●)) --- M6((●))
           M7((●)) --- M8((●)) --- M9((●))
           M1 --- M4 --- M7
           M2 --- M5 --- M8
           M3 --- M6 --- M9
       end

**Star**: Remove center = Total collapse.
**Mesh**: Remove any node = Network survives.

Narrative Events
----------------

The TopologyMonitor generates narrative events at key thresholds:

.. list-table:: Narrative Triggers
   :header-rows: 1
   :widths: 30 70

   * - Condition
     - Narrative
   * - ``percolation < 0.1``
     - "STATE: Gaseous. Movement is atomized."
   * - ``percolation crosses 0.5``
     - "PHASE SHIFT: Condensation detected. A Vanguard Party has formed."
   * - ``potential > 2 × actual``
     - "WARNING: Movement is broad but brittle. Lacks cadre discipline."
   * - ``resilience = False``
     - "ALERT: Sword of Damocles active. A purge would destroy the movement."

The Bondi Algorithm Aesthetic
-----------------------------

Narrative output follows the **Bondi Algorithm** aesthetic—cold,
mechanical precision like a machine cataloging targets:

**Bad (emotional):**
   "The police are cracking down on protesters."

**Good (algorithmic):**
   "High-centrality nodes identified. Degree centrality > 0.4.
   Executing targeted removal. Network fragmentation imminent.
   Probability of survival: 12%."

The horror of state repression is amplified by clinical language.
The machine doesn't hate—it calculates.

Implementation
--------------

The TopologyMonitor implements the ``SimulationObserver`` protocol:

.. code-block:: python

   from babylon.engine import TopologyMonitor

   # Create monitor with resilience testing every 5 ticks
   monitor = TopologyMonitor(
       resilience_test_interval=5,
       resilience_removal_rate=0.2
   )

   # Use with Simulation
   simulation = Simulation(
       state=initial_state,
       config=config,
       observers=[monitor]
   )

   # Run simulation
   simulation.run(max_ticks=100)

   # Access history
   for snapshot in monitor.history:
       print(f"Tick {snapshot.tick}: percolation={snapshot.percolation_ratio:.2f}")

Data Models
-----------

**TopologySnapshot**

.. code-block:: python

   class TopologySnapshot(BaseModel):
       tick: int
       num_components: int
       max_component_size: int       # L_max
       total_nodes: int              # N
       percolation_ratio: Probability
       potential_liquidity: int
       actual_liquidity: int
       is_resilient: bool | None     # None if not tested this tick

**ResilienceResult**

.. code-block:: python

   class ResilienceResult(BaseModel):
       is_resilient: bool
       original_max_component: int
       post_purge_max_component: int
       removal_rate: float
       survival_threshold: float
       seed: int | None              # For reproducibility

Strategic Implications
----------------------

For revolutionary strategy in the simulation:

1. **Monitor percolation ratio**
   Below 0.5, the movement cannot coordinate. Above 0.5, collective
   action becomes possible.

2. **Build actual liquidity**
   Sympathizer networks (potential) are insufficient. Cadre networks
   (actual) provide organizational depth.

3. **Avoid star topology**
   Distributed leadership survives purges. Charismatic-leader
   structures are fragile.

4. **Time the phase transition**
   Strike when condensation occurs—the moment of maximum coordination
   capacity before state response.

See Also
--------

- :doc:`/concepts/topology` - SOLIDARITY edge mechanics
- :doc:`/concepts/george-jackson-model` - Consciousness routing
- :doc:`/api/engine` - TopologyMonitor API reference
- :py:class:`babylon.engine.TopologyMonitor` - Implementation
