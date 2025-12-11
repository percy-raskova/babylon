Analyze Parameter Sensitivity
=============================

This guide shows how to systematically explore how parameter changes affect
simulation outcomes. Use these techniques to understand the design space,
identify stable ranges, and validate theoretical predictions.

Prerequisites
-------------

- Completed :doc:`/tutorials/first-simulation`
- Basic understanding of :doc:`/concepts/imperial-rent`
- Access to ``mise`` task runner

Available Tools
---------------

Babylon provides two analysis modes via ``tools/parameter_analysis.py``:

**Trace Mode**
   Run a single simulation and capture full time-series data.
   Useful for detailed analysis of one parameter configuration.

**Sweep Mode**
   Run multiple simulations varying one parameter.
   Useful for identifying thresholds and phase transitions.

Single-Run Trace Analysis
-------------------------

Capture complete state evolution for detailed analysis:

.. code-block:: bash

   mise run analyze-trace

This creates ``results/trace.csv`` with columns:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Description
   * - ``tick``
     - Simulation tick number
   * - ``p_w_wealth``
     - Periphery worker (C001) wealth
   * - ``p_w_psa``
     - P(S|A) - survival by acquiescence
   * - ``p_w_psr``
     - P(S|R) - survival by revolution
   * - ``p_w_consciousness``
     - Class consciousness level
   * - ``exploitation_tension``
     - Tension on exploitation edge
   * - ``exploitation_rent``
     - Imperial rent extracted this tick

Custom Parameter Values
~~~~~~~~~~~~~~~~~~~~~~~

Override a specific parameter for the trace:

.. code-block:: bash

   poetry run python tools/parameter_analysis.py trace \
       --param economy.extraction_efficiency=0.1 \
       --csv results/low_extraction_trace.csv

This runs with extraction efficiency at 10% instead of the default 80%.

Extended Runs
~~~~~~~~~~~~~

For longer simulations:

.. code-block:: bash

   poetry run python tools/parameter_analysis.py trace \
       --ticks 200 \
       --csv results/extended_trace.csv

Parameter Sweep Analysis
------------------------

Explore how outcomes change across a parameter range:

.. code-block:: bash

   mise run analyze-sweep

Default sweep varies ``economy.extraction_efficiency`` from 0.05 to 0.50
in steps of 0.05. Output goes to ``results/sweep.csv``.

Custom Sweeps
~~~~~~~~~~~~~

Sweep any GameDefines parameter:

.. code-block:: bash

   poetry run python tools/parameter_analysis.py sweep \
       --param consciousness.drift_sensitivity_k \
       --start 0.1 \
       --end 2.0 \
       --step 0.1 \
       --csv results/consciousness_sweep.csv

Sweep Output Columns
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Description
   * - ``value``
     - Parameter value tested
   * - ``ticks_survived``
     - How many ticks before death (or max)
   * - ``outcome``
     - SURVIVED or DIED
   * - ``final_p_w_wealth``
     - Worker wealth at simulation end
   * - ``max_tension``
     - Peak tension observed
   * - ``crossover_tick``
     - Tick when P(S|R) exceeded P(S|A)
   * - ``cumulative_rent``
     - Total rent extracted across all ticks
   * - ``peak_p_w_consciousness``
     - Maximum consciousness reached

Interpreting Results
--------------------

Identifying Thresholds
~~~~~~~~~~~~~~~~~~~~~~

Look for parameter values where outcomes change dramatically:

**Death Threshold**
   The extraction efficiency where ``ticks_survived`` drops sharply.
   Below this value, workers survive; above, they die quickly.

**Crossover Point**
   The first ``value`` where ``crossover_tick`` becomes non-null.
   This indicates when revolution becomes rational.

**Consciousness Ceiling**
   Compare ``peak_p_w_consciousness`` across values.
   Higher extraction may paradoxically increase consciousness before death.

Validating Theory
~~~~~~~~~~~~~~~~~

MLM-TW predicts specific relationships:

1. **Higher extraction → faster death**
   ``ticks_survived`` should decrease as ``extraction_efficiency`` increases.

2. **Higher extraction → more rent**
   ``cumulative_rent`` should increase with efficiency (until death).

3. **More tension → earlier crossover**
   ``crossover_tick`` should be inversely related to ``max_tension``.

If your results contradict these predictions, either:

- The parameter range is outside theoretical validity
- There's a bug in the simulation (see :doc:`debug-simulation-outcomes`)
- The theory needs refinement (document as discovery)

Visualizing Results
-------------------

Import sweep CSV into your preferred analysis tool:

**Python (pandas + matplotlib)**:

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt

   df = pd.read_csv("results/sweep.csv")

   fig, axes = plt.subplots(2, 2, figsize=(12, 10))

   # Survival vs extraction
   axes[0, 0].plot(df["value"], df["ticks_survived"])
   axes[0, 0].set_xlabel("Extraction Efficiency")
   axes[0, 0].set_ylabel("Ticks Survived")
   axes[0, 0].set_title("Survival Time")

   # Rent accumulation
   axes[0, 1].plot(df["value"], df["cumulative_rent"])
   axes[0, 1].set_xlabel("Extraction Efficiency")
   axes[0, 1].set_ylabel("Cumulative Rent")
   axes[0, 1].set_title("Total Extraction")

   # Peak consciousness
   axes[1, 0].plot(df["value"], df["peak_p_w_consciousness"])
   axes[1, 0].set_xlabel("Extraction Efficiency")
   axes[1, 0].set_ylabel("Peak Consciousness")
   axes[1, 0].set_title("Consciousness Development")

   # Crossover timing
   crossover = df[df["crossover_tick"].notna()]
   axes[1, 1].scatter(crossover["value"], crossover["crossover_tick"])
   axes[1, 1].set_xlabel("Extraction Efficiency")
   axes[1, 1].set_ylabel("Crossover Tick")
   axes[1, 1].set_title("Revolution Threshold")

   plt.tight_layout()
   plt.savefig("results/sweep_analysis.png")

**Spreadsheet**:
   Import CSV, create line charts for each metric vs. parameter value.

Available Parameters
--------------------

All parameters in GameDefines can be swept. Common ones:

**Economy**:
   - ``economy.extraction_efficiency`` - How much rent extracted per tick
   - ``economy.base_subsistence`` - Minimum wealth for survival

**Consciousness**:
   - ``consciousness.drift_sensitivity_k`` - How fast consciousness changes
   - ``consciousness.agitation_accumulation_rate`` - Agitation buildup speed

**Solidarity**:
   - ``solidarity.transmission_rate`` - How fast consciousness spreads
   - ``solidarity.decay_rate`` - How fast solidarity weakens

**Survival**:
   - ``survival.loss_aversion_lambda`` - Kahneman-Tversky loss aversion

See :doc:`/reference/configuration` for the complete parameter list.

Best Practices
--------------

1. **Start with wide sweeps**, then narrow to interesting regions
2. **Document your findings** in ``brainstorm/analysis/``
3. **Compare against theory** - unexpected results are discoveries
4. **Use consistent tick counts** for comparable results
5. **Version your CSV outputs** for reproducibility

See Also
--------

- :doc:`debug-simulation-outcomes` - Diagnosing unexpected behavior
- :doc:`parameter-tuning` - Manual parameter adjustment
- :doc:`/reference/configuration` - GameDefines parameter reference
- :doc:`/concepts/survival-calculus` - Theoretical foundation
