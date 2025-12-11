Understanding Simulation Systems
================================

This guide explains how Babylon's modular simulation systems work together
to produce emergent class struggle dynamics.

Overview
--------

Each simulation tick, the engine runs a sequence of **Systems** that
transform the world state. Systems are modular, testable, and follow
a strict protocol.

.. code-block:: text

   WorldState (tick N)
        │
        ▼
   ┌─────────────────────────────────────────────────────┐
   │  SimulationEngine.run_tick()                        │
   │                                                     │
   │  1. ImperialRentSystem   - Extract tribute          │
   │  2. SolidaritySystem     - Transmit consciousness   │
   │  3. ConsciousnessSystem  - Drift ideology           │
   │  4. SurvivalSystem       - Calculate probabilities  │
   │  5. ContradictionSystem  - Accumulate tension       │
   │  6. TerritorySystem      - Process heat/eviction    │
   │  7. StruggleSystem       - Agency responses         │
   │                                                     │
   └─────────────────────────────────────────────────────┘
        │
        ▼
   WorldState (tick N+1)

The System Protocol
-------------------

All systems implement the ``System`` protocol:

.. code-block:: python

   from typing import Protocol

   class System(Protocol):
       def process(
           self,
           graph: nx.DiGraph,
           services: ServiceContainer,
           context: TickContext
       ) -> None:
           """Mutate graph according to system logic."""
           ...

**Parameters:**

- ``graph``: NetworkX DiGraph to mutate (nodes and edges)
- ``services``: Dependency injection container (EventBus, FormularRegistry)
- ``context``: Tick metadata (tick number, config, delta_time)

**Contract:**

- Systems MUST only mutate the graph
- Systems MUST NOT hold state between ticks
- Systems MAY emit events via ``services.event_bus``
- Systems SHOULD use formulas from ``services.formula_registry``

System Execution Order
----------------------

Systems run in a specific order because later systems depend on
calculations from earlier systems:

1. ImperialRentSystem
^^^^^^^^^^^^^^^^^^^^^

**Purpose:** Extract wealth via EXPLOITATION edges.

**Inputs:** EXPLOITATION edges, tribute rates

**Outputs:** Updated wealth values, TRIBUTE edge flows

.. code-block:: python

   # Simplified logic
   for edge in graph.edges(data=True):
       if edge["edge_type"] == EdgeType.EXPLOITATION:
           tribute = edge["rate"] * source_wealth
           graph.nodes[target]["wealth"] -= tribute
           graph.nodes[source]["wealth"] += tribute

2. SolidaritySystem
^^^^^^^^^^^^^^^^^^^

**Purpose:** Transmit class consciousness via SOLIDARITY edges.

**Inputs:** SOLIDARITY edges, consciousness values

**Outputs:** Updated consciousness, decayed solidarity strengths

.. code-block:: python

   # Consciousness spreads along SOLIDARITY edges
   for edge in solidarity_edges:
       source_consciousness = graph.nodes[source]["consciousness"]
       transmission = source_consciousness * transmission_rate
       graph.nodes[target]["consciousness"] += transmission

   # Solidarity edges decay over time
   for edge in solidarity_edges:
       edge["solidarity_strength"] *= decay_rate

3. ConsciousnessSystem
^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** Apply George Jackson bifurcation to ideology.

**Inputs:** Agitation levels, SOLIDARITY presence

**Outputs:** Updated ideology values (-1 to +1)

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

4. SurvivalSystem
^^^^^^^^^^^^^^^^^

**Purpose:** Calculate survival probabilities P(S|A) and P(S|R).

**Inputs:** Wealth, organization, repression values

**Outputs:** Updated P_acquiescence, P_revolution values

.. code-block:: python

   # Survival by acquiescence
   P_S_A = sigmoid(wealth - subsistence_threshold)

   # Survival by revolution
   P_S_R = organization / max(repression, epsilon)

   graph.nodes[node]["P_acquiescence"] = P_S_A
   graph.nodes[node]["P_revolution"] = P_S_R

5. ContradictionSystem
^^^^^^^^^^^^^^^^^^^^^^

**Purpose:** Accumulate tension from contradictions between classes.

**Inputs:** Class attributes, contradiction definitions

**Outputs:** Updated tension values, potential rupture flags

.. code-block:: python

   for contradiction in active_contradictions:
       tension_delta = calculate_tension_increase(contradiction, graph)
       graph.nodes[node]["tension"] += tension_delta

       if graph.nodes[node]["tension"] > rupture_threshold:
           flag_potential_rupture(node, graph)

6. TerritorySystem
^^^^^^^^^^^^^^^^^^

**Purpose:** Process territorial heat, eviction, and displacement.

**Inputs:** Territory heat, operational profiles, TENANCY edges

**Outputs:** Updated heat, displaced classes, detention states

.. code-block:: python

   for territory in territories:
       # Decay heat
       territory["heat"] *= (1 - heat_decay)

       # Add heat from activities
       territory["heat"] += calculate_activity_heat(territory)

       # Trigger eviction if above threshold
       if territory["heat"] >= heat_threshold:
           evict_classes(territory, graph)

7. StruggleSystem
^^^^^^^^^^^^^^^^^

**Purpose:** Implement agency responses (EXCESSIVE_FORCE → UPRISING).

**Inputs:** Repression events, organization levels

**Outputs:** Uprising events, changed class states

.. code-block:: python

   # When state uses EXCESSIVE_FORCE
   if excessive_force_event:
       affected_class = event.target

       # High organization + excessive force = uprising
       if graph.nodes[affected_class]["organization"] > uprising_threshold:
           trigger_uprising(affected_class, graph)
           services.event_bus.emit(UprisingEvent(class_id=affected_class))

Creating Custom Systems
-----------------------

You can create custom systems for new mechanics:

.. code-block:: python

   from babylon.engine.systems.protocol import System

   class PropagandaSystem:
       """System for ideological propaganda effects."""

       def __init__(self, effectiveness: float = 0.1):
           self.effectiveness = effectiveness

       def process(self, graph, services, context):
           for node_id, data in graph.nodes(data=True):
               if data.get("_node_type") != "social_class":
                   continue

               # Propaganda pushes ideology toward 0 (apolitical)
               current = data["ideology"]
               drift = -current * self.effectiveness
               graph.nodes[node_id]["ideology"] = current + drift

Registering Custom Systems
--------------------------

Add systems to the engine's system list:

.. code-block:: python

   from babylon.engine import SimulationEngine

   engine = SimulationEngine()
   engine.register_system(PropagandaSystem(effectiveness=0.05))

Or configure via ``SimulationConfig``:

.. code-block:: python

   config = SimulationConfig(
       additional_systems=[
           PropagandaSystem(effectiveness=0.05)
       ]
   )

Formula Integration
-------------------

Systems should use the FormulaRegistry for calculations:

.. code-block:: python

   class SurvivalSystem:
       def process(self, graph, services, context):
           formulas = services.formula_registry

           for node_id, data in graph.nodes(data=True):
               # Use registered formula (allows hot-swapping)
               P_S_A = formulas.calculate_acquiescence_probability(
                   wealth=data["wealth"],
                   subsistence=context.config.subsistence_threshold
               )
               graph.nodes[node_id]["P_acquiescence"] = P_S_A

This enables:

- Testing with mock formulas
- Runtime formula changes for experimentation
- Consistent formula usage across systems

Event Emission
--------------

Systems can emit events for observers:

.. code-block:: python

   from babylon.engine import Event

   class RuptureEvent(Event):
       class_id: str
       tension_level: float

   class ContradictionSystem:
       def process(self, graph, services, context):
           for node_id, data in graph.nodes(data=True):
               if data["tension"] > rupture_threshold:
                   services.event_bus.emit(
                       RuptureEvent(
                           class_id=node_id,
                           tension_level=data["tension"]
                       )
                   )

Testing Systems
---------------

Systems are designed for easy testing:

.. code-block:: python

   import pytest
   from babylon.engine.systems import SurvivalSystem
   from babylon.engine import ServiceContainer, EventBus

   @pytest.fixture
   def minimal_graph():
       G = nx.DiGraph()
       G.add_node("C001", _node_type="social_class", wealth=100, organization=0.5)
       return G

   @pytest.fixture
   def services():
       return ServiceContainer(
           event_bus=EventBus(),
           formula_registry=FormulaRegistry()
       )

   def test_survival_calculation(minimal_graph, services):
       system = SurvivalSystem()
       context = TickContext(tick=0, config=SimulationConfig())

       system.process(minimal_graph, services, context)

       assert "P_acquiescence" in minimal_graph.nodes["C001"]
       assert 0 <= minimal_graph.nodes["C001"]["P_acquiescence"] <= 1

Debugging Systems
-----------------

Use logging to trace system execution:

.. code-block:: python

   import logging

   class ConsciousnessSystem:
       def __init__(self):
           self.logger = logging.getLogger(__name__)

       def process(self, graph, services, context):
           self.logger.debug(f"Tick {context.tick}: Processing consciousness")

           for node_id, data in graph.nodes(data=True):
               old_ideology = data["ideology"]
               # ... calculation ...
               self.logger.debug(
                   f"  {node_id}: ideology {old_ideology:.2f} → {new_ideology:.2f}"
               )

Enable debug logging:

.. code-block:: python

   logging.getLogger("babylon.engine.systems").setLevel(logging.DEBUG)

See Also
--------

- :doc:`/concepts/architecture` - Overall system architecture
- :doc:`/guides/configuration` - Configuring system parameters
- :py:mod:`babylon.engine.systems` - System implementations
- :py:class:`babylon.engine.ServiceContainer` - Dependency injection
