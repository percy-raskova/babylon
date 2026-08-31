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

   mise run sim:sweep

Pass a tick limit as the optional positional argument when a shorter exploratory
run is sufficient:

.. code-block:: bash

   mise run sim:sweep 1040

Run Global Sensitivity Analysis
-------------------------------

Use the optimization package for Morris screening, Sobol decomposition, or both:

.. code-block:: bash

   mise run tune:morris
   mise run tune:sobol

The direct entry point exposes the combined mode:

.. code-block:: bash

   uv run python -m babylon.engine.optimization sensitivity --method both

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
