Debug Simulation Outcomes
=========================

This guide helps you diagnose unexpected simulation results systematically.
Use these techniques when outcomes don't match theoretical predictions or
when values fall outside expected ranges.

Prerequisites
-------------

- Completed :doc:`/tutorials/first-simulation`
- Basic understanding of :doc:`/concepts/survival-calculus`
- Access to ``mise`` task runner

Symptom Identification
----------------------

Before debugging, identify which symptom you're experiencing:

**Values Out of Range**
   - Probability values outside [0, 1]
   - Negative wealth
   - Consciousness exceeding bounds

**Unexpected Bifurcation**
   - Fascism when solidarity edges exist
   - Revolution without sufficient P(S|R)
   - Stalled consciousness drift

**Timing Issues**
   - Death occurring too early/late
   - Crossover threshold never reached
   - Rent extraction not accumulating

Step 1: Verify Formula Correctness
----------------------------------

Run the formula doctests to ensure mathematical operations work correctly:

.. code-block:: bash

   mise run doctest

This validates all formulas in ``src/babylon/systems/formulas.py`` against
their documented examples. If tests fail, the bug is in formula implementation.

.. seealso::

   :doc:`/reference/formulas` for the complete formula specification.

Step 2: Run a Trace Analysis
----------------------------

Capture full simulation state over time:

.. code-block:: bash

   mise run analyze-trace

This outputs a CSV to ``results/trace.csv`` with per-tick data:

- Entity wealth, consciousness, organization
- Survival probabilities (P(S|A), P(S|R))
- Edge tension and value flows

Open the CSV in a spreadsheet to identify:

- **Inflection points**: Where do values change direction?
- **Correlations**: Do related values move together?
- **Anomalies**: Any sudden jumps or flat periods?

Step 3: Use Structured Logging
------------------------------

For detailed event-by-event debugging, use the vertical slice tool:

.. code-block:: bash

   poetry run python tools/vertical_slice.py

This tool provides:

1. **Tick-by-tick state display**: All entity values per tick
2. **Event logging**: What events triggered each state change
3. **JSON structured logs**: Machine-readable logs in ``logs/``

Interpreting JSON Logs
~~~~~~~~~~~~~~~~~~~~~~

The ``logs/vertical_slice_<timestamp>.json`` file contains:

.. code-block:: json

   {
     "event_type": "simulation_tick",
     "data": {
       "tick": 5,
       "entities": {
         "C001_periphery_worker": 0.0823,
         "C004_labor_aristocracy": 0.2156
       },
       "economy": {
         "imperial_rent_pool": 0.15,
         "super_wage_rate": 0.08
       },
       "tension": 0.42,
       "events": ["SURPLUS_EXTRACTION: 0.018 from C001"]
     }
   }

Search the JSON for:

- ``"event_type": "error"`` to find logged errors
- ``"success": false`` to find failed operations
- Specific entity IDs to trace their state changes

Step 4: Compare Against Theory
------------------------------

Use the survival calculus formulas to verify expected behavior:

**P(S|A) Should**:
   - Increase when wealth increases
   - Approach 0 as wealth approaches subsistence threshold
   - Follow sigmoid curve centered at subsistence level

**P(S|R) Should**:
   - Increase with organization
   - Decrease with repression
   - Cross P(S|A) when revolution becomes rational choice

**Bifurcation Should**:
   - Route to fascism when solidarity edges absent
   - Route to revolution when solidarity edges present
   - Trigger when wages fall and agitation increases

.. seealso::

   :doc:`/concepts/george-jackson-model` for bifurcation theory.

Step 5: Isolate the Problem
---------------------------

Once you've identified which system is misbehaving:

**For formula bugs**:
   Create a minimal test case in ``tests/unit/formulas/``.

**For system bugs**:
   Check the relevant system in ``src/babylon/systems/``:

   - ``economic.py`` - Imperial rent extraction
   - ``solidarity.py`` - Consciousness transmission
   - ``ideology.py`` - Bifurcation and drift
   - ``survival.py`` - P(S|A) and P(S|R)

**For graph bugs**:
   Use ``state.to_graph()`` to inspect the NetworkX graph directly:

   .. code-block:: python

      from babylon.engine.scenarios import create_imperial_circuit_scenario

      state, config, defines = create_imperial_circuit_scenario()
      G = state.to_graph()

      # Inspect edges
      print(list(G.edges(data=True)))

      # Check for missing solidarity edges
      solidarity_edges = [
          (u, v) for u, v, d in G.edges(data=True)
          if d.get("type") == "SOLIDARITY"
      ]

Common Failure Patterns
-----------------------

Death at Tick 1
~~~~~~~~~~~~~~~

**Symptom**: Periphery worker dies immediately.

**Cause**: Initial wealth below subsistence threshold combined with high
extraction efficiency.

**Fix**: Check ``extraction_efficiency`` in GameDefines or increase initial
periphery wealth in scenario.

P(S|R) Always Zero
~~~~~~~~~~~~~~~~~~

**Symptom**: Revolution probability never increases.

**Cause**: Organization value not increasing, or repression too high.

**Fix**: Verify solidarity edges exist and ``organization`` field updates.

Consciousness Never Drifts
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: ``class_consciousness`` stays constant.

**Cause**: Missing solidarity edges (required for transmission) or
``drift_sensitivity_k`` set too low.

**Fix**: Check graph structure for SOLIDARITY edges between entities.

Fascism Without Trigger
~~~~~~~~~~~~~~~~~~~~~~~

**Symptom**: Ideology shifts to +1 without visible cause.

**Cause**: Agitation accumulated while solidarity edges were absent.

**Fix**: Review edge creation in scenario setup; ensure solidarity edges
added before agitation triggers.

Getting Help
------------

If you've followed these steps and still can't identify the issue:

1. Create a minimal reproduction script
2. Include the trace CSV output
3. Note which tick the unexpected behavior occurs
4. Check existing tests for similar scenarios

See Also
--------

- :doc:`analyze-parameter-sensitivity` - Systematic parameter exploration
- :doc:`parameter-tuning` - Adjusting GameDefines values
- :doc:`/reference/formulas` - Complete formula specifications
- :doc:`/reference/error-codes` - Error code reference
