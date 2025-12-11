Guides
======

.. note::

   **Documentation Reorganization**

   This section is being reorganized into Diataxis-compliant quadrants:

   - **Tutorials** moved to :doc:`/tutorials/index` (learning-oriented)
   - **How-To Guides** moved to :doc:`/how-to/index` (task-oriented)

   The remaining guides below will be split into proper quadrants in Phase 2.

Understanding the Engine
------------------------

.. toctree::
   :maxdepth: 1

   simulation-systems
   configuration

These comprehensive guides cover both how the engine works and how to
configure it. They will be split into separate tutorial, how-to, and
explanation documents in a future update.

**Simulation Systems**
   Understand how the seven core systems (ImperialRent, Solidarity,
   Consciousness, Survival, Contradiction, Territory, Struggle)
   work together to produce emergent behavior.

**Configuration**
   Learn to tune simulation parameters using ``GameDefines``, run
   parameter sweeps, and understand sensitivity analysis.

Quick Reference
---------------

**Run simulation:**

.. code-block:: bash

   poetry run python -m babylon

**Run tests:**

.. code-block:: bash

   poetry run pytest -m "not ai"    # Fast tests
   poetry run pytest -m "ai"        # AI evaluation tests

**Parameter analysis:**

.. code-block:: bash

   mise run analyze-trace           # Single run with CSV output
   mise run analyze-sweep           # Multi-parameter sweep

See Also
--------

- :doc:`/tutorials/index` - Learning-oriented guides for newcomers
- :doc:`/how-to/index` - Task-oriented guides for specific goals
- :doc:`/concepts/index` - Deep explanations of why things work
- :doc:`/reference/index` - Quick lookup for APIs and settings
