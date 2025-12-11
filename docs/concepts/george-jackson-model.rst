George Jackson Bifurcation Model
================================

The George Jackson model describes how economic crisis routes consciousness
toward either **class solidarity** or **national identity** (fascism),
depending on the presence of solidarity networks.

Named after the revolutionary theorist George Jackson, this model captures
a critical insight: material conditions alone do not determine revolutionary
outcomes—organizational infrastructure matters.

Theoretical Foundation
----------------------

When wages fall and material conditions deteriorate, agitation energy
increases. But where does this energy go?

**Without SOLIDARITY edges:**
   Energy routes toward national/racial identity → Fascism (+1 ideology)

**With SOLIDARITY edges:**
   Energy routes toward class consciousness → Revolution (-1 ideology)

This creates a **bifurcation** in ideological space:

.. mermaid::

   flowchart TB
       A[Agitation Energy] --> B{SOLIDARITY<br/>Edge Present?}
       B -->|No| C[FASCISM<br/>+ideology +1.0]
       B -->|Yes| D[REVOLUTION<br/>-ideology -1.0]
       C --> E[National/Racial<br/>Identity]
       D --> F[Class<br/>Consciousness]

The Ideology Axis
-----------------

Babylon models ideology on a continuous scale:

.. list-table:: Ideology Scale
   :header-rows: 1
   :widths: 20 80

   * - Value
     - Meaning
   * - -1.0
     - Revolutionary class consciousness
   * - 0.0
     - Apolitical / acquiescent
   * - +1.0
     - National/racial identity (fascism)

The scale represents not moral value but **organizational allegiance**:

- Negative values → International proletarian solidarity
- Positive values → National/imperial identification

Consciousness Drift Formula
---------------------------

Consciousness drift is calculated each tick:

.. math::

   \Delta I = k \cdot A \cdot D

Where:

- :math:`\Delta I` = Change in ideology
- :math:`k` = Drift sensitivity coefficient (from GameDefines)
- :math:`A` = Agitation level (from material conditions)
- :math:`D` = Direction (+1 or -1, determined by SOLIDARITY presence)

**Agitation Level:**

Agitation increases when:

- Wages fall below subsistence
- Wealth declines over time
- Imperial rent extraction intensifies

**Direction Determination:**

.. code-block:: python

   def determine_direction(class_node, graph):
       """Determine ideological direction from solidarity network."""
       solidarity_edges = [
           e for e in graph.edges(class_node)
           if graph.edges[e]["edge_type"] == EdgeType.SOLIDARITY
       ]
       if solidarity_edges:
           return -1  # Class consciousness
       else:
           return +1  # National identity

Empirical Validation
--------------------

The George Jackson model has been validated through parameter sweep
analysis with the following findings:

**Key Parameter: solidarity_decay_base**

.. list-table:: Sweep Results
   :header-rows: 1
   :widths: 20 40 40

   * - Decay Rate
     - Outcome
     - Ideology Range
   * - 0.90
     - Revolution (tick ~30)
     - [-1.0, -0.8]
   * - 0.95
     - Stalemate
     - [-0.5, 0.5]
   * - 0.99
     - Fascism (tick ~50)
     - [0.8, 1.0]

The solidarity decay rate determines whether class networks persist
long enough to route agitation toward revolution.

Historical Parallel
-------------------

The model captures the historical pattern observed by George Jackson
and other revolutionary theorists:

1. **Weimar Germany (1929-1933)**
   - Economic crisis (wages fell)
   - Weak KPD solidarity networks
   - Agitation routed → National Socialism

2. **Russia (1905-1917)**
   - Economic crisis (wages fell)
   - Strong Bolshevik organizational networks
   - Agitation routed → October Revolution

3. **USA (2008-2016)**
   - Economic crisis (wages stagnated)
   - Weak labor/socialist networks
   - Agitation routed → Trump/MAGA nationalism

Implementation
--------------

The bifurcation logic is implemented in the ConsciousnessSystem:

.. code-block:: python

   # src/babylon/engine/systems/ideology.py

   class ConsciousnessSystem:
       def process(self, graph, services, context):
           for node_id, data in graph.nodes(data=True):
               if data.get("_node_type") != "social_class":
                   continue

               # Calculate agitation from material conditions
               agitation = self._calculate_agitation(node_id, data, graph)

               # Determine direction from solidarity network
               direction = self._determine_direction(node_id, graph)

               # Apply consciousness drift
               drift = self.drift_sensitivity * agitation * direction
               new_ideology = clamp(data["ideology"] + drift, -1.0, 1.0)

               graph.nodes[node_id]["ideology"] = new_ideology

Key Parameters
--------------

The following ``GameDefines`` parameters control bifurcation behavior:

.. list-table:: Configuration Parameters
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Default
     - Effect
   * - ``consciousness.drift_sensitivity_k``
     - 0.1
     - How fast ideology changes
   * - ``consciousness.agitation_threshold``
     - 0.3
     - Minimum agitation to trigger drift
   * - ``solidarity.decay_base``
     - 0.95
     - How fast SOLIDARITY edges decay
   * - ``solidarity.transmission_rate``
     - 0.1
     - How fast consciousness spreads

Strategic Implications
----------------------

For revolutionary movements in the simulation:

1. **Build SOLIDARITY edges early**
   Without organizational infrastructure, crisis will route to fascism.

2. **Maintain solidarity networks**
   Higher decay rates favor fascism; strong networks favor revolution.

3. **Crisis is necessary but not sufficient**
   Material degradation creates agitation, but organization determines
   its direction.

See Also
--------

- :doc:`/concepts/survival-calculus` - How agents choose acquiescence vs revolution
- :doc:`/concepts/topology` - SOLIDARITY edge dynamics
- :doc:`/concepts/percolation-theory` - Network condensation and resilience
- :py:mod:`babylon.engine.systems.ideology` - Implementation details
