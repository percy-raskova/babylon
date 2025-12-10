Babylon: The Fall of America
============================

A geopolitical simulation engine modeling the collapse of American hegemony
through Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory.

**Graph + Math = History**

.. note::

   This project is under active development.

Overview
--------

Babylon models class struggle not as random events, but as a deterministic
output of material conditions within a compact topological phase space.
The simulation uses:

- **Imperial Rent** (Φ): The difference between core wages and value produced
- **Unequal Exchange**: Value transfer from periphery to core
- **Survival Calculus**: Agent behavior driven by P(S|A) vs P(S|R)

Quick Links
-----------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   guides/index
   concepts/index
   api/index

Getting Started
---------------

Installation
^^^^^^^^^^^^

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/percy-raskova/babylon.git
   cd babylon

   # Install dependencies with Poetry
   poetry install

   # Run the test suite
   poetry run pytest -m "not ai"

Project Architecture
--------------------

The system runs locally without external servers, composed of three pillars:

**The Ledger** (SQLite/Pydantic)
   Stores rigid, material state (Economics, Resources, Turn History)

**The Topology** (NetworkX)
   Stores fluid, relational state (Class Solidarity, Tension, Supply Chains)

**The Archive** (ChromaDB)
   Stores semantic history and theory (RAG for AI narrative generation)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
