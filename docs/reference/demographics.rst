Demographics and Mortality
==========================

The Mass Line Refactor
----------------------

The Mass Line Refactor transforms the Babylon simulation from **Agent-as-Person**
(1 agent = 1 individual) to **Agent-as-Block** (1 agent = 1 demographic block
with population). This enables:

1. **Scalable Demographics:** Model populations without per-person agents
2. **Intra-Class Inequality:** Marginal workers can starve even when average
   wealth suffices
3. **Malthusian Dynamics:** Natural population equilibrium based on carrying
   capacity
4. **Grinding Attrition:** Probabilistic mortality replacing binary alive/dead
   checks

Agent-as-Block Paradigm
-----------------------

Previously, each ``SocialClass`` entity represented a single person with binary
survival. Now each entity represents a demographic block:

.. code-block:: python

   class SocialClass:
       population: int = 1       # Block size (default=1 for backward compat)
       inequality: Gini = 0.0    # Intra-class inequality coefficient [0,1]
       wealth: Currency          # Total wealth of the block

**Examples:**

- "The Detroit Working Class" - population=50,000, inequality=0.45
- "The Wall Street Bourgeoisie" - population=10,000, inequality=0.85

The Inequality Coefficient
--------------------------

The ``inequality`` field is a Gini coefficient [0, 1] measuring wealth
distribution within the class:

.. list-table::
   :header-rows: 1

   * - Value
     - Meaning
     - Effect
   * - 0.0
     - Perfect equality
     - Threshold = 1.0× (exact subsistence suffices)
   * - 0.5
     - Moderate inequality
     - Threshold = 1.5× (50% surplus required)
   * - 0.8
     - High inequality
     - Threshold = 1.8× (80% surplus required)
   * - 1.0
     - Maximum tyranny
     - Threshold = 2.0× (impossible to prevent deaths)

The inequality coefficient determines how much **surplus coverage** is required
to prevent ANY deaths:

.. math::

   \text{threshold} = 1.0 + \text{inequality}

The Grinding Attrition Formula
------------------------------

The VitalitySystem implements three phases:

Phase 1: The Drain
^^^^^^^^^^^^^^^^^^

Linear subsistence burn scaled by population:

.. code-block:: python

   cost = (base_subsistence * population) * subsistence_multiplier
   wealth = max(0, wealth - cost)

A block of 100 workers burns 100× what a single worker burns.

Phase 2: Grinding Attrition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Probabilistic mortality based on coverage deficit:

.. code-block:: python

   # Calculate coverage ratio
   wealth_per_capita = wealth / population
   coverage_ratio = wealth_per_capita / subsistence_needs

   # Calculate threshold (increases with inequality)
   threshold = 1.0 + inequality

   # Calculate attrition rate
   if coverage_ratio >= threshold:
       attrition_rate = 0  # Everyone survives
   else:
       deficit = threshold - coverage_ratio
       attrition_rate = clamp(deficit * (0.5 + inequality), 0, 1)

   # Calculate deaths
   deaths = floor(population * attrition_rate)
   population -= deaths

**Key insight:** High inequality raises the coverage threshold.

Phase 3: The Reaper
^^^^^^^^^^^^^^^^^^^

Full extinction check:

- If ``population = 0``: Mark ``active = False``, emit ``ENTITY_DEATH``
- If ``population = 1`` AND ``wealth < consumption_needs``: Traditional binary
  death

The Malthusian Correction
-------------------------

The formula creates natural equilibrium dynamics:

1. **Deaths occur** due to coverage deficit → population decreases
2. **Per-capita wealth increases** (same wealth, fewer people)
3. **Coverage ratio increases** → fewer future deaths
4. **Population stabilizes** at carrying capacity

**Key:** Wealth is NOT reduced when people die. Per-capita wealth automatically
rises for survivors.

Example equilibrium (inequality=0.5):

.. code-block:: text

   Tick 1: pop=1000, wealth=10, coverage=1.0, threshold=1.5 → deaths=500
   Tick 2: pop=500,  wealth=10, coverage=2.0, threshold=1.5 → deaths=0
   Equilibrium: coverage exceeds threshold

Population-Scaled Systems
-------------------------

The Mass Line paradigm extends to all systems dependent on population:

.. list-table::
   :header-rows: 1

   * - System
     - Metric
     - Treatment
   * - VitalitySystem
     - Mortality
     - Per-capita (coverage ratio)
   * - ProductionSystem
     - Output
     - Aggregate × population
   * - MetabolismSystem
     - Consumption
     - Aggregate × population
   * - SurvivalSystem
     - P(S|A)
     - Per-capita

The Causal Chain
^^^^^^^^^^^^^^^^

1. **VitalitySystem:** Deaths reduce population → per-capita wealth rises
2. **ProductionSystem:** Smaller population produces less total wealth
3. **MetabolismSystem:** Smaller population consumes less biocapacity
4. **SurvivalSystem:** Lower per-capita wealth → lower P(S|A)
5. **Equilibrium:** Population stabilizes at carrying capacity

Events
------

POPULATION_ATTRITION
^^^^^^^^^^^^^^^^^^^^

Emitted when coverage deficit causes deaths:

.. code-block:: python

   {
       "entity_id": "C001",
       "deaths": 500,
       "remaining_population": 500,
       "attrition_rate": 0.5
   }

ENTITY_DEATH
^^^^^^^^^^^^

Emitted on full extinction (population = 0):

.. code-block:: python

   {
       "entity_id": "C001",
       "wealth": 0.0,
       "consumption_needs": 0.01,
       "cause": "extinction"  # or "starvation" for single-person
   }

Backward Compatibility
----------------------

Default values preserve old behavior:

- ``population = 1``: Single-agent scenarios unchanged
- ``inequality = 0.0``: Marginal wealth = average wealth
- Phase 3 preserves binary death check for ``population = 1``

Existing scenarios continue to work without modification.

Theoretical Basis
-----------------

The Mass Line refactor implements key Marxist concepts:

- **Primitive Accumulation:** High inequality reflects dispossession
- **Reserve Army of Labor:** Deaths create downward wage pressure
- **Crisis of Social Reproduction:** Marginal workers can't reproduce themselves
- **Metabolic Rift:** Ecological limits manifest through population dynamics

The name "Mass Line" references the Maoist principle of learning from the
masses---the simulation now models demographic blocks rather than abstract
individuals.

See Also
--------

- :doc:`/concepts/theory` - MLM-TW theoretical foundation
- :doc:`systems` - System reference including VitalitySystem
- :doc:`formulas` - Mathematical formulas
