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

From Compiled Defaults
^^^^^^^^^^^^^^^^^^^^^^

Construct the immutable Pydantic defaults compiled into ``GameDefines``:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()

From the Repository YAML
^^^^^^^^^^^^^^^^^^^^^^^^

Load the canonical repository coefficient payload when it is present:

.. code-block:: python

   defines = GameDefines.load_default()

``GameDefines`` is a ``BaseModel``, not a settings model. It does not ingest
``BABYLON_*`` environment variables implicitly.

From Code
^^^^^^^^^

Override specific parameters programmatically:

.. code-block:: python

   from babylon.config.defines import EconomyDefines, GameDefines

   defines = GameDefines(
       economy=EconomyDefines(extraction_efficiency=0.9)
   )

From an Explicit YAML File
^^^^^^^^^^^^^^^^^^^^^^^^^^

Load and validate a complete YAML payload explicitly:

.. code-block:: python

   from pathlib import Path

   defines = GameDefines.load_from_yaml(Path("src/babylon/data/defines.yaml"))

Run the Frozen Reference Backend
--------------------------------

``SimulationConfig`` now carries only its run-scoped RNG seed; it does not
contain ``max_ticks`` or ``defines``. The development-only runner accepts those
arguments explicitly:

.. code-block:: python

   from babylon.config.defines import GameDefines
   from tools.devtools.sim_analysis.runner_api import run

   result = run(
       GameDefines(economy={"extraction_efficiency": 0.9}),
       backend="in_memory",
       scenario="imperial_circuit",
       max_ticks=100,
       seed=42,
   )

Run Parameter Analysis
----------------------

Parameter Sweep
^^^^^^^^^^^^^^^

Test multiple parameter values systematically:

.. code-block:: bash

   mise run analysis:sweep

This produces ``results/sweep.csv`` with one row per point and the columns
below, plus ``results/sweep.manifest.json`` with the base defines, exact
values, run configuration, results, and verification receipts:

.. code-block:: text

   defines_hash,final_wealth,max_tension,outcome,rng_seed,score,terminal_outcome,ticks_survived,value

Use these artifacts to compare bounded frozen-reference trials. They do not
establish the behavior of a Rust-owned durable campaign.

Sensitivity Analysis
^^^^^^^^^^^^^^^^^^^^

Use the retained development-only analysis package for global sensitivity
analysis:

.. code-block:: bash

   uv run python -m tools.devtools.sim_analysis sensitivity --method both

This is in-memory design-analysis periphery. It does not establish behavior or
authority for a Rust-owned durable campaign. The safe default screens eight
curated parameters with Morris and runs Sobol only on the top four; pass an
explicit comma-separated ``--param-names`` subset for another bounded study.

Prefer Explicit Paths
---------------------

Use full ``category.field`` paths in the analysis commands and change one
coefficient at a time for an exploratory sweep. For multi-parameter designs,
use the bounded sensitivity or Bayesian commands rather than maintaining
hand-written scenario snippets in this guide.

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
