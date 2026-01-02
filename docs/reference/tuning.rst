The 20-Year Entropy Standard
============================

Parameter Tuning Methodology
----------------------------

   **The simulation no longer asks: "Can the empire survive?"**
   **It now asks: "How does the empire die?"**

The default state of the simulation is **COLLAPSE**. Stability is a temporary
deviation, not the norm. We model a 20-year timeline (1040 ticks) because that
is sufficient to observe the systematic decay of any imperial system operating
under capitalist extraction.

The Problem: Eden Mode
----------------------

Previous specifications permitted infinite stability because:

1. **Existence was free:** ``base_subsistence = 0.0`` meant entities persisted
   without cost
2. **Earth was infinite:** No hysteresis in biocapacity degradation
3. **Zombies were possible:** Entities survived with near-zero wealth indefinitely

This produced "flatline" simulations where nothing happened.

The Solution: Dying World Physics
---------------------------------

Under the new standard:

1. **Existence costs calories:** ``base_subsistence > 0.0`` always (The Calorie Check)
2. **Death is real:** VitalitySystem kills entities when ``wealth < consumption_needs``

The 20-Year Benchmark
---------------------

.. list-table::
   :header-rows: 1

   * - Old Standard
     - New Standard
   * - 52 ticks (1 year)
     - 1040 ticks (20 years)

**Why 20 years?**

- Long enough to observe TRPF (Tendency of the Rate of Profit to Fall)
- Long enough for ecological degradation to compound
- Long enough for generational effects
- Short enough for meaningful simulation runs (~10-20 minutes)

Success Criteria
^^^^^^^^^^^^^^^^

**OLD:** "Success = Survival"

**NEW:** "Success = Realistic Decay"

The ideal simulation produces:

- ``p_c_wealth`` declining ~0.05% per tick
- ``total_biocapacity`` declining ~0.08% per tick
- ``imperial_rent_pool`` exhibiting TRPF (declining rate of return)
- Death occurring in the 800-900 tick range (Year 15-17)

The Calorie Check
-----------------

**INVARIANT:** ``base_subsistence > 0.0`` in ALL scenarios

This is the foundational constraint that prevents Eden Mode.

.. code-block:: python

   # FORBIDDEN - Creates Zombie States
   defines.economy.base_subsistence = 0.0  # NEVER

   # REQUIRED - Ensures Entropy
   defines.economy.base_subsistence >= 0.01  # ALWAYS

Every scenario factory and test fixture MUST verify:

.. code-block:: python

   def create_scenario():
       defines = GameDefines()
       assert defines.economy.base_subsistence > 0.0, \
           "Eden Mode detected: base_subsistence must be > 0.0"
       return state, config, defines

Objective Function
------------------

The optimization objective rewards realistic decay:

.. code-block:: python

   def objective_v2(trial):
       """Optimize for REALISTIC DECAY, not survival."""
       result = run_simulation(trial.params, max_ticks=1040)

       # Death Timing (40%): Should occur around tick 850
       death_tick = result.death_tick or 1040
       timing_score = 1.0 - abs(death_tick - 850) / 400

       # Decay Shape (30%): Smooth decline, not flatline or cliff
       decay_smoothness = calculate_curve_smoothness(result.wealth_timeseries)

       # TRPF Manifestation (20%): Rate of profit declines
       trpf_score = calculate_declining_rate(result.rent_pool_timeseries)

       # Biocapacity Exhaustion (10%): Near-zero around death
       exhaustion_score = 1.0 - (result.final_biocapacity / result.initial_biocapacity)

       return (0.4 * timing_score +
               0.3 * decay_smoothness +
               0.2 * trpf_score +
               0.1 * exhaustion_score)

Anti-Patterns
-------------

Zombie State (Flatline)
^^^^^^^^^^^^^^^^^^^^^^^

- **Symptom:** Wealth graph is horizontal
- **Cause:** ``base_subsistence = 0.0`` or consumption_needs too low
- **Detection:** ``std(wealth_timeseries) < 0.01``
- **Fix:** Increase consumption_needs, verify Calorie Check

Instant Death (Cliff)
^^^^^^^^^^^^^^^^^^^^^

- **Symptom:** Simulation ends before tick 100
- **Cause:** Extraction too aggressive, initial wealth too low
- **Detection:** ``death_tick < 100``
- **Fix:** Reduce extraction_efficiency, increase initial wealth

Eternal Empire (Eden Mode)
^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Symptom:** Survives 1040 ticks without significant decay
- **Cause:** Extraction perfectly balanced with production
- **Detection:** ``wealth[tick_1000] / wealth[tick_0] > 0.9``
- **Fix:** Enable biocapacity hysteresis, increase entropy_factor

Hollow Stability
^^^^^^^^^^^^^^^^

- **Symptom:** Metrics oscillate around stable point
- **Cause:** System finds equilibrium (theoretically impossible)
- **Detection:** ``mean(wealth[500:1000]) ≈ mean(wealth[0:500])``
- **Fix:** Increase TRPF coefficient, add extraction hysteresis

Parameter Ranges
----------------

Entropy Parameters
^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Range
     - Purpose
   * - ``economy.base_subsistence``
     - [0.01, 0.05]
     - Calorie drain per tick
   * - ``metabolism.entropy_factor``
     - [1.1, 1.5]
     - Extraction inefficiency

TRPF Parameters
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Range
     - Purpose
   * - ``economy.trpf_coefficient``
     - [0.0001, 0.001]
     - Rate of profit decay
   * - ``economy.rent_pool_decay``
     - [0.001, 0.005]
     - Background rent evaporation

Workflow
--------

1. **Verify Calorie Check:**

   .. code-block:: bash

      poetry run python -c "
      from babylon.config.defines import GameDefines
      d = GameDefines()
      assert d.economy.base_subsistence > 0.0
      print('Calorie Check: PASSED')"

2. **Run 20-Year Simulation:**

   .. code-block:: bash

      mise run sim:trace --ticks 1040

3. **Verify Decay Curve:**

   Review the generated CSV for realistic decay patterns.

See Also
--------

- :doc:`/concepts/theory` - The Tragedy of Inevitability
- :doc:`configuration` - GameDefines reference
- :doc:`formulas` - Mathematical formulas including TRPF
