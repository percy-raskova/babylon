Add a Custom System
===================

This guide walks you through creating, registering, and testing custom
simulation systems to extend Babylon's mechanics.

Prerequisites
-------------

- Familiarity with :doc:`/concepts/simulation-systems`
- Understanding of NetworkX graph operations
- Python class implementation

Create a System Class
---------------------

Systems implement the ``System`` protocol. Here's a complete example—a
``PropagandaSystem`` that pushes ideology toward apolitical (0):

.. code-block:: python

   from babylon.engine.systems.protocol import System


   class PropagandaSystem:
       """System for ideological propaganda effects.

       Propaganda reduces class consciousness by pushing ideology
       toward 0 (apolitical center).
       """

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

**Key requirements:**

1. Implement ``process(graph, services, context)`` method
2. Only mutate the ``graph`` parameter
3. Do not store state between ticks (stateless design)

Register Your System
--------------------

Method 1: Direct Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add systems directly to the engine:

.. code-block:: python

   from babylon.engine import SimulationEngine

   engine = SimulationEngine()
   engine.register_system(PropagandaSystem(effectiveness=0.05))

Method 2: Via SimulationConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pass systems through configuration:

.. code-block:: python

   from babylon.models import SimulationConfig

   config = SimulationConfig(
       additional_systems=[
           PropagandaSystem(effectiveness=0.05)
       ]
   )

Use the Formula Registry
------------------------

For calculations that might need to be swapped or tested, use the
``FormulaRegistry`` from services:

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

**Benefits:**

- Testing with mock formulas
- Runtime formula changes for experimentation
- Consistent formula usage across systems

Emit Events
-----------

Systems can emit events for observers via the EventBus:

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

Events enable loose coupling between systems and observers (like the
TopologyMonitor or narrative generators).

Test Your System
----------------

Systems are designed for isolated testing:

.. code-block:: python

   import pytest
   import networkx as nx
   from babylon.engine import ServiceContainer, EventBus
   from babylon.engine.formula_registry import FormulaRegistry


   @pytest.fixture
   def minimal_graph():
       G = nx.DiGraph()
       G.add_node(
           "C001",
           _node_type="social_class",
           wealth=100,
           organization=0.5,
           ideology=0.0
       )
       return G


   @pytest.fixture
   def services():
       return ServiceContainer(
           event_bus=EventBus(),
           formula_registry=FormulaRegistry()
       )


   def test_propaganda_reduces_consciousness(minimal_graph, services):
       # Arrange
       minimal_graph.nodes["C001"]["ideology"] = 0.8
       system = PropagandaSystem(effectiveness=0.1)
       context = TickContext(tick=0, config=SimulationConfig())

       # Act
       system.process(minimal_graph, services, context)

       # Assert
       new_ideology = minimal_graph.nodes["C001"]["ideology"]
       assert new_ideology < 0.8  # Ideology moved toward 0
       assert new_ideology == pytest.approx(0.72)  # 0.8 - (0.8 * 0.1)

**Testing tips:**

- Create minimal graphs with only necessary nodes
- Test one behavior per test function
- Use ``pytest.approx()`` for floating-point comparisons

Debug Your System
-----------------

Add logging to trace system execution:

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
               new_ideology = data["ideology"]
               self.logger.debug(
                   f"  {node_id}: ideology {old_ideology:.2f} -> {new_ideology:.2f}"
               )

Enable debug logging:

.. code-block:: python

   import logging

   logging.getLogger("babylon.engine.systems").setLevel(logging.DEBUG)

Or via environment variable:

.. code-block:: bash

   export BABYLON_LOG_LEVEL=DEBUG

See Also
--------

- :doc:`/concepts/simulation-systems` - Why systems work this way
- :doc:`/reference/systems` - API reference for built-in systems
- :doc:`parameter-tuning` - Configure system parameters
- :py:mod:`babylon.engine.systems` - System implementations
