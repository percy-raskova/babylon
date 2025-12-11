Babylon: The Fall of America
============================

A geopolitical simulation engine modeling the collapse of American hegemony
through Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory.

**Graph + Math = History**

.. note::

   This project is under active development. See the :doc:`/tutorials/first-simulation`
   to get started.

What is Babylon?
----------------

Babylon models class struggle not as random events, but as a **deterministic
output of material conditions** within a compact topological phase space.

The simulation implements:

- **Imperial Rent** (Φ): Value extraction from periphery to core
- **Survival Calculus**: Agents maximize P(S|A) vs P(S|R)
- **George Jackson Model**: Consciousness bifurcation (revolution vs fascism)
- **Percolation Theory**: Phase transitions in solidarity networks
- **Carceral Geography**: Detention, displacement, elimination pipelines

Architecture Overview
---------------------

The system runs locally without external servers, using the **Embedded Trinity**:

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Layer
     - Technology
     - Purpose
   * - **The Ledger**
     - SQLite / Pydantic
     - Rigid material state (wealth, organization)
   * - **The Topology**
     - NetworkX
     - Fluid relational state (solidarity, exploitation)
   * - **The Archive**
     - ChromaDB
     - Semantic history for AI narrative

See :doc:`/concepts/architecture` for detailed architecture documentation.

Quick Start
-----------

.. code-block:: bash

   # Install dependencies
   git clone https://github.com/percy-raskova/babylon.git
   cd babylon
   poetry install

   # Run tests
   poetry run pytest -m "not ai"

   # Run simulation
   poetry run python -m babylon

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/index

.. toctree::
   :maxdepth: 2
   :caption: How-To Guides

   how-to/index

.. toctree::
   :maxdepth: 2
   :caption: Concepts

   concepts/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 2
   :caption: Legacy Guides

   guides/index

Current Systems
---------------

**Implemented:**

- Imperial Rent extraction (EXPLOITATION edges)
- Consciousness drift and bifurcation (George Jackson model)
- Solidarity transmission (SOLIDARITY edges)
- Survival calculus (P(S|A), P(S|R))
- Territory dynamics (heat, eviction, displacement)
- Agency layer (EXCESSIVE_FORCE → UPRISING)
- Topology monitoring (percolation, resilience testing)

**In Development:**

- Narrative generation (AI observer)
- Full game UI (NiceGUI)

Mathematical Core
-----------------

**Fundamental Theorem of MLM-TW:**

.. math::

   \text{Revolution in Core impossible when } W_c > V_c

Where :math:`W_c` is core wages and :math:`V_c` is value produced.
The difference is Imperial Rent (Φ).

**Survival Calculus:**

.. math::

   P(S|A) = \text{Sigmoid}(W - S_{min})

   P(S|R) = \frac{O}{R}

Rupture occurs when :math:`P(S|R) > P(S|A)`.

See :doc:`/concepts/imperial-rent` and :doc:`/concepts/survival-calculus`
for detailed explanations.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
