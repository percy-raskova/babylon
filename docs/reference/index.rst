Reference
=========

Technical reference documentation for the Babylon simulation engine.

Simulation Protocols
--------------------

.. toctree::
   :maxdepth: 1

   simulation-protocols

GUI-facing protocols (``SimulationState``, ``SimulationControl``) and snapshot
models (``TerritoryState``, ``HexState``, ``SimulationSnapshot``). These define
the stable interface boundary for GUI development.

Data Models
-----------

.. toctree::
   :maxdepth: 1

   data-models
   tensor
   tensor-primitive
   precision

Complete specification of data structures, entity collections, constrained
types, graph structure, the Marxian value tensor (ValueTensor4x3), tensor
registry and hydration pipeline, and the Gatekeeper Pattern for quantization.

Mathematical Formulas
---------------------

.. toctree::
   :maxdepth: 1

   formulas
   class-dynamics
   economics-pipeline
   volume-i-production

All simulation formulas: imperial rent, survival calculus, consciousness
drift, solidarity transmission, dynamic balance, class wealth dynamics ODEs,
the economics pipeline (capital stock, MELT, throughput, visibility, class
dynamics), and Capital Volume I production dynamics.

Organization Base Model (Feature 031)
-------------------------------------

.. toctree::
   :maxdepth: 1

   organizations

OODA Loop System (Feature 032)
-------------------------------

.. toctree::
   :maxdepth: 1

   ooda-loop-system
   ooda-coefficients

Entity models (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg),
discriminated union dispatch, composition calculators, consciousness effect
formula, topology classification, key figure analysis, and legacy migration.

Simulation Systems
------------------

.. toctree::
   :maxdepth: 1

   systems
   community-system
   lifecycle-system
   circulation-system
   demographics

API reference for the simulation systems, the community hypergraph layer
(Feature 022), the D-P-D' lifecycle circuit (Feature 030), the Capital
Volume II circulation layer (Feature 023), and demographics mechanics
including the Mass Line population block paradigm.

Persistence Layer (Feature 037)
-------------------------------

.. toctree::
   :maxdepth: 1

   persistence

Protocols (``RuntimePersistence``, ``VectorStoreProtocol``, ``TraceCollector``),
concrete implementations (``PostgresRuntime``, ``RuntimeDatabase``,
``PgVectorStore``, ``TraceRecorder``), database schema, and the
``PersistenceObserver`` lifecycle hook.

Economic Data Sources
---------------------

.. toctree::
   :maxdepth: 1

   census-analysis
   fred-data
   qcew-data

Empirical data sources for Marxian analysis:

- **Census ACS**: Labor aristocracy identification, rent burden, class composition
- **FRED**: CPI, wages, unemployment, fiscal indicators, PPP metrics
- **QCEW**: Employment/wages by county, state, and metro area with hybrid API/file loading

Tensor Hierarchy (Feature 025)
-------------------------------

.. toctree::
   :maxdepth: 1

   tensor-hierarchy
   tensor-hierarchy-schema
   bea-io-tables
   faf-freight-data
   bea-department-mapping

Multi-level tensor hierarchy data dictionary: all nine tensor types and
protocols, the six new SQLite tables, BEA Input-Output data format and
loader API, BTS FAF5 freight data format and loader API, and the complete
BEA-to-Marxian-department industry classification mapping.

Event System
------------

.. toctree::
   :maxdepth: 1

   events
   interceptor

Complete reference for the typed event system: 11 EventTypes, 13 event classes,
event lifecycle, factory methods, and the Interceptor pattern for adversarial mechanics.

Configuration
-------------

.. toctree::
   :maxdepth: 1

   configuration
   tuning

Configuration system documentation, environment variables, GameDefines
parameter tables, and the 20-Year Entropy Standard for parameter tuning.

Topology System
---------------

.. toctree::
   :maxdepth: 1

   topology
   dialectical-field-topology

Percolation theory metrics, TopologyMonitor observer, resilience testing,
and the dialectical field topology framework (contradiction fields,
derivatives, curvature, edge mode state machine).

Infrastructure Topology (Feature 036)
-------------------------------------

.. toctree::
   :maxdepth: 1

   infrastructure-topology

Terrain classification, typed infrastructure on H3 mesh edges, biocapacity
extraction, nonlocal edges, internet consciousness field operations, and
configuration parameters.

Design System
-------------

.. toctree::
   :maxdepth: 1

   design-system

Visual design tokens: color palette, typography, styling constants, and
texture specifications for Bunker Constructivism aesthetic.

Documentation System
--------------------

.. toctree::
   :maxdepth: 1

   documentation

Build commands, Sphinx extensions, LaTeX configuration, and PDF theme
specifications. Meta-reference for the documentation engine itself.

AI & RAG
--------

.. toctree::
   :maxdepth: 1

   ai-prompting
   context-window-api

Prompt templates, API usage patterns, and context window management API.

Error Handling
--------------

.. toctree::
   :maxdepth: 1

   error-codes

Error code taxonomy and error handling conventions.

CI/CD Workflow
--------------

.. toctree::
   :maxdepth: 1

   ci-workflow

GitHub Actions workflows, branch protection rules, and the Benevolent
Dictator governance model.
