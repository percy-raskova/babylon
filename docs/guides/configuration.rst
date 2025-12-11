Configuration Guide
===================

This guide explains how to configure Babylon's simulation parameters
using the centralized ``GameDefines`` system.

Overview
--------

Babylon uses a **data-driven configuration** approach:

- All tunable parameters are externalized to ``GameDefines``
- No magic numbers in code—every coefficient has a name
- Parameters are grouped by system (economy, consciousness, etc.)
- Defaults can be overridden via environment or code

GameDefines Structure
---------------------

The ``GameDefines`` class is a Pydantic model with nested configuration:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()

   # Access nested parameters
   defines.economy.extraction_efficiency     # 0.8
   defines.consciousness.drift_sensitivity_k # 0.1
   defines.solidarity.decay_base             # 0.95
   defines.survival.subsistence_threshold    # 0.2
   defines.territory.heat_threshold          # 0.8

Configuration Categories
------------------------

Economy Parameters
^^^^^^^^^^^^^^^^^^

Control imperial rent extraction and wealth flows:

.. list-table:: Economy Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``extraction_efficiency``
     - 0.8
     - Fraction of surplus captured as imperial rent
   * - ``tribute_rate``
     - 0.1
     - Base rate of tribute extraction per tick
   * - ``wage_floor``
     - 0.05
     - Minimum wage (prevents zero-wealth)
   * - ``wealth_transfer_rate``
     - 0.15
     - Rate of wealth movement along edges

Consciousness Parameters
^^^^^^^^^^^^^^^^^^^^^^^^

Control ideology drift and bifurcation:

.. list-table:: Consciousness Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``drift_sensitivity_k``
     - 0.1
     - How fast ideology changes per tick
   * - ``agitation_threshold``
     - 0.3
     - Minimum agitation to trigger drift
   * - ``consciousness_cap``
     - 1.0
     - Maximum consciousness value
   * - ``bifurcation_enabled``
     - True
     - Enable George Jackson model

Solidarity Parameters
^^^^^^^^^^^^^^^^^^^^^

Control SOLIDARITY edge dynamics:

.. list-table:: Solidarity Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``decay_base``
     - 0.95
     - Solidarity decay per tick (0.95 = 5% decay)
   * - ``transmission_rate``
     - 0.1
     - Consciousness spread along edges
   * - ``formation_threshold``
     - 0.3
     - Consciousness needed to form new edges
   * - ``min_strength``
     - 0.05
     - Edges below this are pruned

Survival Parameters
^^^^^^^^^^^^^^^^^^^

Control survival calculus:

.. list-table:: Survival Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``subsistence_threshold``
     - 0.2
     - Wealth level for basic survival
   * - ``sigmoid_steepness``
     - 10.0
     - Steepness of P(S|A) sigmoid curve
   * - ``loss_aversion``
     - 2.0
     - Kahneman-Tversky loss aversion factor
   * - ``revolution_damping``
     - 0.5
     - Reduces P(S|R) (revolution is risky)

Territory Parameters
^^^^^^^^^^^^^^^^^^^^

Control carceral geography:

.. list-table:: Territory Parameters
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``heat_threshold``
     - 0.8
     - Heat level triggering eviction
   * - ``heat_decay``
     - 0.1
     - Heat reduction per tick
   * - ``spillover_coefficient``
     - 0.2
     - Heat transferred on displacement
   * - ``detention_duration``
     - 5
     - Ticks in detention before incarceration
   * - ``displacement_priority``
     - BALANCED
     - Default mode (LABOR_SCARCE/BALANCED/ELIMINATION)

Loading Configuration
---------------------

From Defaults
^^^^^^^^^^^^^

.. code-block:: python

   from babylon.config.defines import GameDefines

   # Load with defaults
   defines = GameDefines()

From Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   export BABYLON_ECONOMY_EXTRACTION_EFFICIENCY=0.9
   export BABYLON_CONSCIOUSNESS_DRIFT_SENSITIVITY_K=0.15

.. code-block:: python

   # Environment variables are loaded automatically
   defines = GameDefines()
   assert defines.economy.extraction_efficiency == 0.9

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

From Code
^^^^^^^^^

.. code-block:: python

   from babylon.config.defines import GameDefines, EconomyDefines

   defines = GameDefines(
       economy=EconomyDefines(
           extraction_efficiency=0.9,
           tribute_rate=0.15
       )
   )

Using with SimulationConfig
---------------------------

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

   # Use in simulation
   simulation = Simulation(state=initial_state, config=config)

Parameter Tuning Workflow
-------------------------

Babylon includes tools for parameter exploration:

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

Parameter Sweep
^^^^^^^^^^^^^^^

Test multiple parameter values:

.. code-block:: bash

   mise run analyze-sweep

This produces ``results/sweep.csv`` with summary metrics:

.. code-block:: text

   solidarity_decay,revolution_tick,final_ideology,final_tension
   0.90,32,-0.85,0.95
   0.95,None,0.12,0.45
   0.99,None,0.78,0.22

Sensitivity Analysis
^^^^^^^^^^^^^^^^^^^^

Use the parameter tuning tool:

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

Best Practices
--------------

1. **Start with Defaults**
   The defaults are calibrated for reasonable behavior. Adjust one
   parameter at a time.

2. **Use Parameter Sweeps**
   Don't guess—run sweeps to understand parameter effects.

3. **Document Changes**
   When modifying parameters for specific scenarios, document why.

4. **Validate Against Theory**
   Parameters should produce outcomes consistent with MLM-TW theory.

Common Parameter Combinations
-----------------------------

**High Exploitation Scenario**

.. code-block:: python

   defines = GameDefines(
       economy={"extraction_efficiency": 0.95, "tribute_rate": 0.2}
   )

**Strong Solidarity Scenario**

.. code-block:: python

   defines = GameDefines(
       solidarity={"decay_base": 0.98, "transmission_rate": 0.2}
   )

**High Repression Scenario**

.. code-block:: python

   defines = GameDefines(
       territory={"heat_threshold": 0.5, "displacement_priority": "ELIMINATION"}
   )

Debugging Configuration
-----------------------

Print current configuration:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()
   print(defines.model_dump_json(indent=2))

Validate configuration:

.. code-block:: python

   # Pydantic validates automatically
   try:
       defines = GameDefines(economy={"extraction_efficiency": 1.5})
   except ValidationError as e:
       print(f"Invalid: {e}")  # extraction_efficiency must be <= 1.0

See Also
--------

- :doc:`/concepts/architecture` - How configuration fits into the system
- :doc:`/guides/simulation-systems` - How systems use parameters
- :py:mod:`babylon.config.defines` - GameDefines API reference
