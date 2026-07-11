.. _tensor-hierarchy-reference:

=================================
Tensor Hierarchy Reference
=================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Complete data dictionary for all tensor types, protocols, default
implementations, and validation rules introduced in Feature 025.

For architectural context, see :ref:`tensor-hierarchy-concept`.
For theory behind the math, see :ref:`leontief-analysis`,
:ref:`imperial-rent-field`, and :ref:`class-mobility`.

----

Level 1 Tensor Types
====================

InterIndustryFlow
-----------------

.. class:: InterIndustryFlow

   BEA input-output direct requirements coefficient matrix.
   Level 1 tensor sourced from ``fact_bea_io_coefficient``.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - BEA data year. Constraint: ≥ 1997.
      * - ``table_type``
        - ``IOTableType``
        - Which BEA table this was derived from. Default: ``USE``.
      * - ``industries``
        - ``list[str]``
        - Ordered list of BEA Summary-level industry codes (~70 items).
      * - ``coefficients``
        - ``np.ndarray``
        - Direct requirements matrix A, shape ``(n, n)``, ``float64``.

   **Computed property:**

   - ``n_industries`` → ``int``: Number of industries (length of ``industries``).

   **Constraints:** ``coefficients.shape == (n, n)`` where ``n = len(industries)``.

   **Source:** :class:`~babylon.domain.economics.tensor_hierarchy.inter_industry.DefaultInterIndustryFlowSource`
   reads from ``fact_bea_io_coefficient`` populated by
   :class:`~babylon.data.bea.io_loader.BEAIOLoader`.


IOTableType
-----------

.. class:: IOTableType

   Enum for BEA I-O table classification.

   .. list-table::
      :header-rows: 1
      :widths: 20 80

      * - Value
        - Description
      * - ``USE``
        - Use table (commodity-by-industry intermediate use). Basis for direct
          requirements coefficients A[i,j]. This is the primary source.
      * - ``MAKE``
        - Make table (industry-by-commodity output structure).
      * - ``SUPPLY``
        - Supply table (total supply of commodities from all sources).
      * - ``TOTAL_REQ``
        - Total requirements (Leontief inverse as published by BEA).


VisibilityMetric
----------------

.. class:: VisibilityMetric

   Diagonal visibility tensor for the four Marxian departments.
   Wraps Feature 015 gamma module output into the tensor hierarchy.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - Data year. Constraint: ≥ 2003 (ATUS availability).
      * - ``g_diagonal``
        - ``np.ndarray``
        - Visibility diagonal ``[g_11, g_22a, g_22b, g_33]``, shape ``(4,)``.
      * - ``g_11``
        - ``float``
        - Department I visibility. Range: [0.0, 1.0]. Expected: ≈ 0.97.
      * - ``g_22a``
        - ``float``
        - Department IIa visibility. Range: [0.0, 1.0]. Expected: ≈ 0.97.
      * - ``g_22b``
        - ``float``
        - Department IIb visibility. Range: [0.0, 1.0]. Expected: ≈ 0.97.
      * - ``g_33``
        - ``float``
        - Department III visibility (care work). Range: [0.0, 1.0].
          Expected: [0.20, 0.40]. Approximately 1/3 of US care work is
          commodified (ATUS data).
      * - ``is_estimated``
        - ``bool``
        - ``True`` if values are estimated/MVP rather than computed from ATUS.
          Default: ``False``.

   **Source:** :class:`~babylon.domain.economics.tensor_hierarchy.visibility.DefaultVisibilitySource`
   wraps :class:`~babylon.domain.economics.gamma.gamma_iii.DefaultGammaIIICalculator`.


GeographicFlow
--------------

.. class:: GeographicFlow

   BTS FAF origin-destination commodity flow matrix.
   Level 1 tensor sourced from ``fact_faf_commodity_flow``.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - FAF data year. Constraint: ≥ 2012 (FAF5 data begins).
      * - ``areas``
        - ``list[str]``
        - Ordered list of CFS Area codes (~130 areas).
      * - ``flow_matrix``
        - ``np.ndarray``
        - O-D flow matrix, shape ``(n, n)``, values in millions USD.
      * - ``commodity_code``
        - ``str | None``
        - SCTG 2-digit code for commodity-specific flow; ``None`` for
          all-commodity aggregate. Default: ``None``.

   **Computed property:**

   - ``n_areas`` → ``int``: Number of CFS areas (length of ``areas``).

   **Constraints:** ``flow_matrix.shape == (n, n)`` where ``n = len(areas)``.

   **Source:** :class:`~babylon.domain.economics.tensor_hierarchy.geographic_flow.DefaultGeographicFlowSource`
   reads from ``fact_faf_commodity_flow`` populated by
   :class:`~babylon.data.bts.faf_loader.FAFLoader`.


ReproductionRequirements
------------------------

.. class:: ReproductionRequirements

   Consumption and reproductive labor requirements by social class.
   Level 1 tensor combining CEX consumer expenditure and ATUS time-use data.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - Data year. Constraint: ≥ 2000.
      * - ``consumption``
        - ``dict``
        - Nested dict: ``class → department → use_value_category → hours``.
          Represents use-value bundles consumed per class per Marxian department.
      * - ``reproductive_labor``
        - ``dict``
        - Nested dict: ``reproduced_class → laborer_class → type → hours``.
          Represents labor performed to reproduce each class.

   .. note::

      Production loader deferred (US4). ``DefaultReproductionSource`` returns
      :class:`~babylon.domain.economics.tensor.NoDataSentinel` for all queries.
      All tests use synthetic data.

   **Source:** :class:`~babylon.domain.economics.tensor_hierarchy.reproduction.DefaultReproductionSource` (stub).


ClassTransitionMatrix
---------------------

.. class:: ClassTransitionMatrix

   Stochastic matrix of class mobility probabilities.
   Level 1 tensor from PSID panel study data.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``period``
        - ``tuple[int, int]``
        - ``(start_year, end_year)`` defining the transition window.
      * - ``classes``
        - ``list[str]``
        - Ordered list of ``SocialRole`` class names.
      * - ``transition_matrix``
        - ``np.ndarray``
        - Row-stochastic matrix, shape ``(n, n)``. Each row sums to 1.0
          (tolerance 1e-6). P[i,j] = probability of class i → class j.

   **Computed property:**

   - ``n_classes`` → ``int``: Number of classes (length of ``classes``).

   **Constraints:** Shape ``(n, n)``, ``n = len(classes)``. Row sums = 1.0 ± 1e-6.

   .. note::

      Production loader deferred (US5). ``DefaultClassTransitionSource`` returns
      :class:`~babylon.domain.economics.tensor.NoDataSentinel`. Computation engine
      (``DefaultClassTransitionComputer``) is fully implemented.

   **Source:** :class:`~babylon.domain.economics.tensor_hierarchy.class_transition.DefaultClassTransitionSource` (stub).

Level 2 Tensor Types
====================

LeontiefInverse
---------------

.. class:: LeontiefInverse

   Total requirements matrix L = (I − A)⁻¹. Level 2 tensor derived from
   :class:`InterIndustryFlow`.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - Same as source ``InterIndustryFlow`` year. Constraint: ≥ 1997.
      * - ``industries``
        - ``list[str]``
        - Same ordered BEA industry codes as source ``InterIndustryFlow``.
      * - ``inverse_matrix``
        - ``np.ndarray``
        - Total requirements matrix (I − A)⁻¹, shape ``(n, n)``.
          All elements ≥ 0. Diagonal ≥ 1.0.

   **Computed property:**

   - ``n_industries`` → ``int``: Number of industries.

   **Mathematical guarantee:** If Hawkins-Simon holds (all column sums of A < 1),
   then: all ``inverse_matrix`` elements ≥ 0, all diagonal elements ≥ 1.0.

   **Computed by:** :class:`~babylon.domain.economics.tensor_hierarchy.inter_industry.DefaultLeontiefComputer`.


ImperialRentField
-----------------

.. class:: ImperialRentField

   Net value extraction (inflow − outflow) per CFS area. Level 2 tensor
   derived from :class:`GeographicFlow`.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - Same as source ``GeographicFlow`` year. Constraint: ≥ 2012.
      * - ``areas``
        - ``list[str]``
        - Same ordered CFS Area codes as source ``GeographicFlow``.
      * - ``phi``
        - ``np.ndarray``
        - Net value extraction per area, shape ``(n_areas,)``, signed,
          millions USD. Positive = core (net importer). Negative = periphery
          (net exporter). Conservation: |Σφ| < 0.01% of total flow.

   **Computed property:**

   - ``n_areas`` → ``int``: Number of CFS areas.

   **Computed by:** :class:`~babylon.domain.economics.tensor_hierarchy.geographic_flow.DefaultImperialRentComputer`.


ShadowSubsidyTensor
-------------------

.. class:: ShadowSubsidyTensor

   Shadow subsidy from un-commodified reproductive labor. Level 2 tensor
   derived from :class:`VisibilityMetric`.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``year``
        - ``int``
        - Reference year. Constraint: ≥ 2000.
      * - ``phi_iii_labor_hours``
        - ``float``
        - Shadow subsidy in labor-hours: Dept III value × (1 − g₃₃). ≥ 0.
      * - ``phi_iii_dollars``
        - ``float | None``
        - Dollar value if MELT (Monetary Expression of Labor Time) is available,
          else ``None``.
      * - ``melt_available``
        - ``bool``
        - Whether MELT was used for the dollar conversion. Default: ``False``.

   **Computed by:** :class:`~babylon.domain.economics.tensor_hierarchy.visibility.DefaultVisibilitySource`.


StationaryDistribution
-----------------------

.. class:: StationaryDistribution

   Long-run class distribution from ClassTransitionMatrix eigenvector.
   Level 2 tensor derived from :class:`ClassTransitionMatrix`.

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Field
        - Type
        - Description
      * - ``period``
        - ``tuple[int, int]``
        - Same ``(start_year, end_year)`` as source ``ClassTransitionMatrix``.
      * - ``classes``
        - ``list[str]``
        - Same ordered class names as source ``ClassTransitionMatrix``.
      * - ``distribution``
        - ``np.ndarray``
        - Stationary distribution π, shape ``(n_classes,)``. All elements ≥ 0.
          Sum = 1.0 (tolerance 1e-6). Satisfies π @ P = π.

   **Computed property:**

   - ``n_classes`` → ``int``: Number of classes.

   **Computed by:** :class:`~babylon.domain.economics.tensor_hierarchy.class_transition.DefaultClassTransitionComputer`.

Source Protocols
================

.. list-table:: Data Source Protocols
   :header-rows: 1
   :widths: 30 30 40

   * - Protocol
     - Methods
     - Returns
   * - ``InterIndustryFlowSource``
     - ``get_direct_requirements(year)``
       ``get_industry_codes()``
       ``available_years()``
     - ``InterIndustryFlow | NoDataSentinel``
       ``list[str]``
       ``frozenset[int]``
   * - ``GeographicFlowSource``
     - ``get_flows(year, commodity_code=None)``
       ``get_cfs_areas()``
       ``get_cfs_to_county_mapping()``
     - ``GeographicFlow | NoDataSentinel``
       ``list[str]``
       ``dict[str, list[str]]``
   * - ``VisibilitySource``
     - ``get_visibility(year)``
       ``get_shadow_subsidy(year, dept_iii_value, melt=None)``
     - ``VisibilityMetric | NoDataSentinel``
       ``ShadowSubsidyTensor | NoDataSentinel``
   * - ``ReproductionSource``
     - ``get_requirements(year)``
       ``total_reproduction_cost(social_class, year, snlt)``
     - ``ReproductionRequirements | NoDataSentinel``
       ``float | NoDataSentinel``
   * - ``ClassTransitionSource``
     - ``get_transition_matrix(period)``
       ``get_stationary_distribution(period)``
     - ``ClassTransitionMatrix | NoDataSentinel``
       ``StationaryDistribution | NoDataSentinel``

Computation Protocols
=====================

.. list-table:: Computation Protocols
   :header-rows: 1
   :widths: 25 35 40

   * - Protocol
     - Methods
     - Returns
   * - ``LeontiefComputer``
     - ``compute_inverse(flow)``
       ``total_labor_coefficients(leontief, direct_labor)``
     - ``LeontiefInverse``
       ``np.ndarray`` (shape: n)
   * - ``ImperialRentComputer``
     - ``compute_rent_field(flow)``
       ``decompose_symmetric_antisymmetric(flow)``
     - ``ImperialRentField``
       ``tuple[np.ndarray, np.ndarray]``
   * - ``DepartmentAggregator``
     - ``aggregate(flow, mapping)``
       ``get_default_mapping()``
     - ``InterIndustryFlow`` (4×4)
       ``dict[str, str]``

All protocols use ``@runtime_checkable``, enabling ``isinstance`` checks at
runtime.

----

Default Implementations
========================

.. list-table:: Protocol → Default Implementation Mapping
   :header-rows: 1
   :widths: 35 35 30

   * - Protocol
     - Default Class
     - Module
   * - ``InterIndustryFlowSource``
     - ``DefaultInterIndustryFlowSource``
     - ``inter_industry``
   * - ``GeographicFlowSource``
     - ``DefaultGeographicFlowSource``
     - ``geographic_flow``
   * - ``VisibilitySource``
     - ``DefaultVisibilitySource``
     - ``visibility``
   * - ``ReproductionSource``
     - ``DefaultReproductionSource`` (stub)
     - ``reproduction``
   * - ``ClassTransitionSource``
     - ``DefaultClassTransitionSource`` (stub)
     - ``class_transition``
   * - ``LeontiefComputer``
     - ``DefaultLeontiefComputer``
     - ``inter_industry``
   * - ``ImperialRentComputer``
     - ``DefaultImperialRentComputer``
     - ``geographic_flow``
   * - ``DepartmentAggregator``
     - ``DefaultDepartmentAggregator``
     - ``inter_industry``

Additional helper classes:

- ``DefaultGeographicAggregator`` — Aggregates CFS area flows to state level.
- ``DefaultClassTransitionComputer`` — Computes stationary distributions and
  class aggregation (not a protocol implementation, a standalone computer).
- ``DefaultReproductionRequirementsComputer`` — Computes reproduction
  requirements from synthetic data (not a protocol implementation).

All implementations are in ``src/babylon/economics/tensor_hierarchy/``.

----

Validation Rules
================

.. list-table:: Three-Tier Validation Thresholds
   :header-rows: 1
   :widths: 25 18 18 18 21

   * - Rule
     - Expected
     - Warning
     - Fail
     - Function
   * - I-O col sum max
     - ≤ 0.90
     - > 0.90
     - ≥ 1.0
     - ``validate_io_column_sums``
   * - Individual coefficient
     - ≤ 0.60
     - > 0.60
     - < 0 or ≥ 1.0
     - (inline)
   * - Leontief elements
     - ≥ 0
     - —
     - < −1e-10
     - ``validate_leontief_properties``
   * - Leontief diagonal
     - ≥ 1.0
     - —
     - < 1.0 − 1e-10
     - ``validate_leontief_properties``
   * - g_33 (Dept III)
     - [0.20, 0.40]
     - [0.10, 0.50]
     - <0 or >1
     - ``validate_g33``
   * - g_11, g_22a, g_22b
     - [0.90, 1.0]
     - [0.70, 1.0]
     - <0 or >1
     - ``validate_g_productive``
   * - Rent conservation
     - \|Σφ\|/total < 0.01%
     - \|Σφ\|/total < 0.1%
     - \|Σφ\|/total ≥ 1%
     - ``validate_rent_conservation``
   * - Transition row sum
     - deviation ≤ 1e-6
     - deviation ≤ 1e-4
     - deviation > 1e-4
     - ``validate_transition_matrix``
   * - Transition diagonal
     - ≥ 0.50
     - ≥ 0.20
     - < 0
     - ``validate_transition_matrix``

All validation functions return ``(bool, str | None)``:
``(True, None)`` = pass, ``(True, str)`` = warning, ``(False, str)`` = fail.

----

Related Documentation
=====================

- :ref:`tensor-hierarchy-concept` — Architecture and design rationale
- :ref:`tensor-hierarchy-schema` — SQLite table definitions
- :ref:`leontief-analysis` — I-O economics theory
- :ref:`imperial-rent-field` — Spatial value extraction theory
- :ref:`class-mobility` — Markov chain class transition theory
- :mod:`babylon.domain.economics.tensor_hierarchy` — Python module
