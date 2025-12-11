Guides
======

Step-by-step tutorials and how-to guides for working with Babylon.

Getting Started
---------------

.. toctree::
   :maxdepth: 1

   installation
   quickstart

New to Babylon? Start here to install dependencies and run your
first simulation.

Understanding the Engine
------------------------

.. toctree::
   :maxdepth: 1

   simulation-systems
   configuration

Learn how the simulation engine works: the modular system architecture,
how to configure parameters, and how to extend the engine.

For Developers
--------------

These guides assume familiarity with Python, Pydantic, and NetworkX.

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

**Build documentation:**

.. code-block:: bash

   mise run docs                    # Build HTML docs
   mise run docs-live               # Live-reload server
