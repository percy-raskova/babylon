.. _tensor-hierarchy-concept:

=============================
Tensor Hierarchy Architecture
=============================

.. contents:: Table of Contents
   :local:
   :depth: 2

Babylon's economic computation uses a **three-level tensor hierarchy** built on
top of the :ref:`Marxian value tensor <tensor-api>`. Each level provides
progressively higher abstractions: raw county-year primitives at Level 0,
federal data sources at Level 1, and derived computations at Level 2.

This document explains *why* the hierarchy exists and *why* each design choice
was made. For the complete data dictionary, see :ref:`tensor-hierarchy-reference`.

----

The Three Levels
================

Level 0: The Primitive
-----------------------

The :class:`~babylon.domain.economics.tensor.ValueTensor4x3` (Feature 011) is the
simulation's foundational type. It represents the 4×3 Marxian reproduction
schema for a single county-year: four departments each decomposed into constant
capital (*c*), variable capital (*v*), and surplus value (*s*). Level 0 is the
output—the thing the simulation engine *consumes*.

Level 1: Federal Data Sources
------------------------------

Level 1 tensors are extracted directly from federal datasets. They represent
empirical economic structure at the national scale, loaded once and shared
across all county-year computations:

**InterIndustryFlow**
  The BEA Use table direct requirements matrix *A*, where *A*\[*i*,*j*] is the
  dollar value of industry *i*'s output required per dollar of industry *j*'s
  output. Covers ~70 BEA Summary-level industries. Source: Bureau of Economic
  Analysis I-O accounts (annual, 1997–2024).

**VisibilityMetric**
  The diagonal visibility tensor *G* = diag(*g*\ :sub:`11`, *g*\ :sub:`22a`,
  *g*\ :sub:`22b`, *g*\ :sub:`33`), measuring what fraction of each Marxian
  department's labor is commodified (visible to the price system). Source: ATUS
  time-use data via the Feature 015 gamma module.

**GeographicFlow**
  The BTS FAF5 origin-destination commodity flow matrix *F*, where *F*\[*a*,*b*]
  is the USD value (millions) of freight shipped from CFS Area *a* to CFS
  Area *b* (~130 areas). Source: Bureau of Transportation Statistics Freight
  Analysis Framework (FAF5), 2022 scale: $18.7T, 2.49M records.

**ReproductionRequirements**
  Consumption bundles and reproductive labor time by social class across the
  four Marxian departments. Source: CEX consumer expenditure survey + ATUS
  time-use data. *Production loader deferred—see US4 below.*

**ClassTransitionMatrix**
  The class mobility stochastic matrix *P*, where *P*\[*i*,*j*] is the
  probability of someone in class *i* transitioning to class *j* over a
  specified period. Source: PSID Panel Study of Income Dynamics.
  *Production loader deferred—see US5 below.*

Level 2: Derived Computations
-------------------------------

Level 2 tensors are derived from Level 1 inputs by mathematical operations.
They have no independent data sources—they are pure functions of Level 1 data:

**LeontiefInverse**
  *L* = (*I* − *A*)\ :sup:`−1`, the total requirements matrix. Captures both
  direct and all indirect supply-chain dependencies embodied in final demand.
  See :ref:`leontief-analysis` for the mathematical theory.

**ImperialRentField**
  φ[*a*] = inflow[*a*] − outflow[*a*], the net value extraction per CFS area.
  Positive values identify core accumulation zones; negative values identify
  periphery extraction zones. For a closed system, Σφ ≈ 0. See
  :ref:`imperial-rent-field` for the mathematical theory.

**ShadowSubsidyTensor**
  Department III value × (1 − *g*\ :sub:`33`): the unpaid reproductive labor
  appropriated as surplus by capital. Quantifies the "invisible" care-work
  contribution that standard national accounts systematically exclude.

**StationaryDistribution**
  The long-run class distribution π satisfying π*P* = π, normalized to sum 1.
  Computed as the dominant left eigenvector of *P*. Represents the gravitational
  pull of class structure toward a long-run equilibrium. See
  :ref:`class-mobility` for the mathematical theory.

Why Three Levels?
-----------------

The hierarchy serves three functions:

**Separation of concerns.** Federal data sources (Level 1) are isolated from
derived computations (Level 2). Adding a new computation requires only a new
computer protocol, not changes to data loading or schema.

**Incremental buildout.** Each Level 1 tensor can be present or absent
independently. US3 (geographic flows, requiring FAF data download) can be
absent without blocking US1 (inter-industry flows, from XLSX already present).
The :class:`~babylon.domain.economics.tensor.NoDataSentinel` makes absence explicit.

**Testability.** Level 2 computations are unit-tested with synthetic Level 1
tensors, without requiring real federal data to be present. The stub pattern
(see deferred loaders below) ensures the composition structure is correct even
before production data is available.

----

Marxian Departments: Theory and Contested Boundaries
=====================================================

The four-department scheme comes from a combination of sources:

- Marx, *Capital Volume II* (1885): two departments (means of production /
  means of consumption)
- Shaikh & Tonak, *Measuring the Wealth of Nations* (1994): split Department
  II into necessary and luxury consumption
- Fortunati, *The Arcane of Reproduction* (1981): Department III for social
  reproduction, the unwaged labor that produces labor power itself

The Four Departments
--------------------

.. list-table:: Marxian Department Classification
   :header-rows: 1
   :widths: 8 22 30 40

   * - Dept
     - Name
     - Theoretical Role
     - BEA Summary Examples
   * - **I**
     - Means of Production
     - Capital goods consumed productively by other industries
     - Mining, Machinery, Construction, Chemicals, Finance, Transport
   * - **IIa**
     - Necessary Consumption
     - Wage goods that reproduce labor power
     - Food & beverage, Textiles, Retail trade, Basic lodging
   * - **IIb**
     - Luxury Consumption
     - Surplus value sink; bourgeois and labor-aristocracy consumption
     - Consumer electronics, Furniture, Gambling, Fine dining, Luxury retail
   * - **III**
     - Social Reproduction
     - Labor power produced outside or at the margin of the wage relation
     - Health care, Education, Social assistance, Private households

The core theoretical point is that Department III is not optional or peripheral—
it is *necessary* for capital accumulation. Every worker who shows up for work
was reproduced by Department III labor. The visibility scalar *g*\ :sub:`33`
measures how much of this labor is commodified (visible) versus performed as
unwaged domestic work (invisible to the price system).

Contested Industry Boundaries
------------------------------

Several industries are genuinely ambiguous. The mapping file captures the
judgment calls with explicit rationale:

**Motor vehicles (BEA 3360A0)** → Department I. Commercial trucks, buses, and
vehicle components dominate by output value. Consumer automobiles are a
boundary case with Department IIb. A commodity-by-industry bridge could split
this, but dominant-use classification puts the sector in I.

**Retail trade (BEA 4400)** → Department IIa. Food and basic household goods
dominate by transaction volume. Luxury retail overlaps with IIb; the mapping
addresses this with separate IIb entries for clothing stores (4481) and
department/general merchandise stores (4521, 4529, 4530).

**Owner-occupied housing (FIRE0)** → Department I. The BEA treats imputed
rental income as capital output, consistent with Shaikh & Tonak's treatment of
housing as a capital asset rather than consumer expenditure.

**Financial intermediation (521CI, 523, 524)** → Department I. Finance enables
productive capital circulation; it is a producer service, not a consumer good.

The mapping lives in
``src/babylon/economics/tensor_hierarchy/mappings/bea_to_department.toml``.
The full industry-by-industry table with rationale notes is in
:ref:`bea-department-mapping`.

----

Protocol-Based Dependency Injection
=====================================

Every tensor source and computation in the hierarchy is a Python
:class:`~typing.Protocol`. No concrete class is hard-coded into computation
pipelines. This enables testing without real data and swapping implementations
without changing callers.

The Source Pattern
------------------

.. code-block:: python

   # Protocol (in protocols.py)
   class InterIndustryFlowSource(Protocol):
       def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel: ...

   # Default implementation (backed by SQLite)
   source = DefaultInterIndustryFlowSource(session_factory)

   # Test stub (backed by synthetic data)
   class StubSource:
       def get_direct_requirements(self, year: int) -> InterIndustryFlow:
           return synthetic_flow_tensor

The Computation Pattern
------------------------

.. code-block:: python

   # Protocol (in protocols.py)
   class LeontiefComputer(Protocol):
       def compute_inverse(self, flow: InterIndustryFlow) -> LeontiefInverse: ...

   # Use the default
   computer = DefaultLeontiefComputer()
   inverse = computer.compute_inverse(flow)

All five source protocols follow the same pattern. All three computation
protocols follow the same pattern. This means the full pipeline can be
instantiated with dependency-injected components, each independently
substitutable.

The NoDataSentinel Pattern
--------------------------

When a data source cannot provide data (missing file, deferred loader, or
absent year), it returns a :class:`~babylon.domain.economics.tensor.NoDataSentinel`
rather than raising an exception. The sentinel is falsy and carries a
human-readable reason:

.. code-block:: python

   result = source.get_direct_requirements(year=1990)
   if not result:
       # Returns reason: "No I-O data for 1990 (BEA tables start 1997)"
       logger.warning("Missing data: %s", result.reason)
   else:
       inverse = computer.compute_inverse(result)

This makes data absence explicit at each call site, prevents silent propagation
of missing-data errors through the pipeline, and avoids exception-based control
flow for expected conditions.

----

Deferred Loaders: US4 and US5
================================

Two Level 1 data sources have production loaders explicitly deferred pending
data governance arrangements:

US4 — ReproductionRequirements
--------------------------------

Production data would come from the Consumer Expenditure Survey (CEX) linked
to ATUS time-use records by class category. This requires BLS microdata
agreements. The ``DefaultReproductionSource`` stub always returns a
``NoDataSentinel`` with reason ``"CEX data source pending (US4 deferred)"``.

The ``DefaultReproductionRequirementsComputer`` is fully implemented and tested
with synthetic data, verifying that the computation structure is correct.

US5 — ClassTransitionMatrix
-----------------------------

Production data would come from the Panel Study of Income Dynamics (PSID),
which requires a restricted-use data agreement with the University of Michigan.
The ``DefaultClassTransitionSource`` stub returns ``NoDataSentinel`` for all
queries, with reason ``"PSID data source pending constitutional amendment (US5
deferred loader)"``.

The ``DefaultClassTransitionComputer`` (eigendecomposition, class aggregation)
is fully implemented and passes all tests with synthetic matrices.

The deferred pattern means that:

1. The computation code is complete and correct.
2. Tests verify the math without requiring real data.
3. When production data becomes available, only the source protocol
   implementation needs to change—no downstream code changes required.

----

Related Documentation
=====================

- :ref:`leontief-analysis` — Why (I − A)⁻¹ and what it means
- :ref:`imperial-rent-field` — Spatial value extraction theory
- :ref:`class-mobility` — Markov chains and stationary class distributions
- :ref:`tensor-hierarchy-reference` — Complete tensor and protocol data dictionary
- :ref:`tensor-hierarchy-schema` — SQLite table definitions for Feature 025
- :ref:`bea-io-tables` — BEA I-O data format and loader API
- :ref:`faf-freight-data` — BTS FAF5 freight data format and loader API
- :ref:`bea-department-mapping` — Full industry-to-department mapping table
- :mod:`babylon.domain.economics.tensor` — Level 0 ValueTensor4x3 primitive
