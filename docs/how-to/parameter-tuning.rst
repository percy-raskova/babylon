Tune Simulation Parameters
==========================

This guide walks you through loading, modifying, and analyzing simulation
parameters using the ``GameDefines`` system.

Prerequisites
-------------

- Basic understanding of the simulation systems
- Familiarity with :doc:`/reference/configuration`

Load Configuration
------------------

From Defaults
^^^^^^^^^^^^^

Load default values (from ``pyproject.toml``):

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()

From Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^

Environment variables override defaults:

.. code-block:: bash

   export BABYLON_ECONOMY_EXTRACTION_EFFICIENCY=0.9
   export BABYLON_CONSCIOUSNESS_DRIFT_SENSITIVITY_K=0.15

.. code-block:: python

   # Environment variables loaded automatically
   defines = GameDefines()
   assert defines.economy.extraction_efficiency == 0.9

From Code
^^^^^^^^^

Override specific parameters programmatically:

.. code-block:: python

   from babylon.config.defines import GameDefines, EconomyDefines

   defines = GameDefines(
       economy=EconomyDefines(
           extraction_efficiency=0.9,
           tribute_rate=0.15
       )
   )

From pyproject.toml
^^^^^^^^^^^^^^^^^^^

Defaults are stored in ``pyproject.toml``:

.. code-block:: toml

   [tool.babylon]
   [tool.babylon.economy]
   extraction_efficiency = 0.8
   tribute_rate = 0.1

   [tool.babylon.consciousness]
   drift_sensitivity_k = 0.1

Use with SimulationConfig
-------------------------

``SimulationConfig`` wraps ``GameDefines`` with simulation-specific options:

.. code-block:: python

   from babylon.models import SimulationConfig
   from babylon.config.defines import GameDefines

   config = SimulationConfig(
       max_ticks=100,
       random_seed=42,
       defines=GameDefines(
           economy={"extraction_efficiency": 0.9}
       )
   )

   # Run simulation with custom parameters
   simulation = Simulation(state=initial_state, config=config)

Run Parameter Analysis
----------------------

Single Trace Analysis
^^^^^^^^^^^^^^^^^^^^^

Run a simulation and export time-series data:

.. code-block:: bash

   mise run analyze-trace

This produces ``results/trace.csv`` with per-tick metrics:

.. code-block:: text

   tick,proletariat_wealth,bourgeoisie_wealth,ideology,tension,...
   0,100.0,500.0,0.0,0.1,...
   1,95.2,510.5,0.05,0.12,...
   ...

Use this to visualize how a single parameter set evolves over time.

Parameter Sweep
^^^^^^^^^^^^^^^

Test multiple parameter values systematically:

.. code-block:: bash

   mise run analyze-sweep

This produces ``results/sweep.csv`` with summary metrics:

.. code-block:: text

   solidarity_decay,revolution_tick,final_ideology,final_tension
   0.90,32,-0.85,0.95
   0.95,None,0.12,0.45
   0.99,None,0.78,0.22

Use this to find parameter values that produce desired outcomes.

Sensitivity Analysis
^^^^^^^^^^^^^^^^^^^^

Programmatically sweep a single parameter:

.. code-block:: python

   from tools.parameter_analysis import sweep_parameter

   results = sweep_parameter(
       param_path="solidarity.decay_base",
       values=[0.90, 0.92, 0.94, 0.96, 0.98],
       ticks=100,
       initial_state=create_two_node_scenario()[0]
   )

   for result in results:
       print(f"decay={result.param_value}: revolution at tick {result.revolution_tick}")

Common Parameter Combinations
-----------------------------

High Exploitation Scenario
^^^^^^^^^^^^^^^^^^^^^^^^^^

Model aggressive imperial rent extraction:

.. code-block:: python

   defines = GameDefines(
       economy={"extraction_efficiency": 0.95, "tribute_rate": 0.2}
   )

**Expected behavior:** Faster wealth transfer, quicker impoverishment of
periphery, potentially faster radicalization.

Strong Solidarity Scenario
^^^^^^^^^^^^^^^^^^^^^^^^^^

Model resilient organizational infrastructure:

.. code-block:: python

   defines = GameDefines(
       solidarity={"decay_base": 0.98, "transmission_rate": 0.2}
   )

**Expected behavior:** Slower solidarity decay, faster consciousness spread,
higher likelihood of revolutionary outcome.

High Repression Scenario
^^^^^^^^^^^^^^^^^^^^^^^^

Model aggressive state response:

.. code-block:: python

   defines = GameDefines(
       territory={"heat_threshold": 0.5, "displacement_priority": "ELIMINATION"}
   )

**Expected behavior:** Lower threshold for eviction, more aggressive
displacement, but potential for backfire via StruggleSystem.

Debug Configuration
-------------------

Print current configuration:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()
   print(defines.model_dump_json(indent=2))

Validate configuration (Pydantic validates automatically):

.. code-block:: python

   from pydantic import ValidationError

   try:
       defines = GameDefines(economy={"extraction_efficiency": 1.5})
   except ValidationError as e:
       print(f"Invalid: {e}")  # extraction_efficiency must be <= 1.0

Best Practices
--------------

1. **Start with defaults**
   The defaults are calibrated for reasonable behavior. Adjust one
   parameter at a time to understand its effect.

2. **Use parameter sweeps**
   Don't guess—run sweeps to understand parameter effects quantitatively.

3. **Document changes**
   When modifying parameters for specific scenarios, document why in
   code comments or commit messages.

4. **Validate against theory**
   Parameters should produce outcomes consistent with MLM-TW theory.
   If high exploitation doesn't lead to radicalization, something is wrong.

5. **Check edge cases**
   Test with extreme values (0.0, 1.0) to ensure the simulation remains
   stable and produces sensible results.

See Also
--------

- :doc:`/reference/configuration` - All parameter reference
- :doc:`/concepts/simulation-systems` - How parameters affect systems
- :doc:`add-custom-system` - Create systems with custom parameters
- :py:mod:`babylon.config.defines` - GameDefines API
