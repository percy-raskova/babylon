Analyze Parameter Sensitivity
=============================

Babylon retains parameter analysis as intentional Python periphery. It explores
the frozen reference model in memory; it does not read or write authoritative
campaign state and cannot prove behavior of the Rust persistence runtime.

Run a One-Dimensional Sweep
---------------------------

The standard sweep varies ``economy.extraction_efficiency`` and writes
``results/sweep.csv``:

.. code-block:: bash

   mise run analysis:sweep

Pass a tick limit as the optional positional argument when a shorter exploratory
run is sufficient:

.. code-block:: bash

   mise run analysis:sweep 1040

Run Global Sensitivity Analysis
-------------------------------

Use the development-only analysis package for Morris screening, Sobol
decomposition, or both:

.. code-block:: bash

   mise run analysis:morris
   mise run analysis:sobol

The direct entry point exposes the combined mode:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis sensitivity --method both

The default combined campaign is intentionally bounded: Morris screens eight
curated parameters with eight trajectories (72 evaluations), then Sobol runs
64 base samples over the top four ``mu*`` parameters (640 evaluations). Each
trial is capped at 2,600 ticks. Override the explicit set through the optional
fourth Mise positional argument or ``--param-names`` on the direct command.

The command refuses an implicit all-fields campaign. It also preflights hard
limits on parameter count, evaluation count, evaluation-ticks, and artifact
size before SALib allocates the design or the reference simulation runs.

``results/morris.json`` and ``results/sobol.json`` retain replay inputs and
verification evidence: the base defines once per phase, bounds and native
types, exact sample vectors, the native overrides actually run, outputs,
seeds, and receipts. Serialization rejects ``NaN`` and infinity, and a
constant objective fails explicitly because sensitivity indices are undefined
at zero output variance.

Treat these results as design exploration. Validate any proposed game-law change
against the governing BSL/Rust contracts and their regression gates before using
it as implementation evidence.

Verify the Authoritative Runtime Separately
-------------------------------------------

Parameter analysis does not substitute for the Rust-owned PostgreSQL/H3 path:

.. code-block:: bash

   mise run sim:e2e-michigan
   mise run sim:probe

See Also
--------

- :doc:`parameter-sweeps` - Optimization package options and output contracts
- :doc:`parameter-tuning` - GameDefines configuration and bounded exploration
- :doc:`debug-simulation-outcomes` - Runtime and reference-model diagnostics
- :doc:`/reference/configuration` - GameDefines parameter reference
