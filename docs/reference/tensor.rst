.. _tensor-api:

=======================
Marxian Value Tensor
=======================

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

The ``ValueTensor4x3`` is the core data structure for Marxian economic analysis
in Babylon. It represents the 4x3 reproduction schema: 4 departments × 3 value
categories (constant capital, variable capital, surplus value).

.. module:: babylon.economics.tensor
   :synopsis: Marxian value tensor models

Classes
=======

DepartmentRow
-------------

.. class:: DepartmentRow

   Value composition for a single Marxian department.

   Represents the three-fold decomposition of commodity value:

   - **c** (constant capital): Value transferred from machinery/materials
   - **v** (variable capital): Value paid to workers as wages
   - **s** (surplus value): Unpaid labor appropriated by capital

   .. attribute:: c
      :type: Currency

      Constant capital (dead labor: machinery, raw materials).
      Must be non-negative.

   .. attribute:: v
      :type: Currency

      Variable capital (living labor: wages).
      Must be non-negative.

   .. attribute:: s
      :type: Currency

      Surplus value (unpaid labor).
      Must be non-negative.

   .. attribute:: total_value
      :type: Currency

      Computed property: ``c + v + s``

   .. attribute:: organic_composition
      :type: float

      Computed property: ``c / v``

      Marx's measure of capital intensity. Higher values indicate more
      mechanization. Returns ``float('inf')`` if ``v = 0``.

   .. attribute:: exploitation_rate
      :type: float

      Computed property: ``s / v``

      The ratio of unpaid labor to paid labor. Returns ``float('inf')`` if ``v = 0``.

   **Example:**

   .. code-block:: python

      >>> from babylon.economics.tensor import DepartmentRow
      >>> row = DepartmentRow(c=100.0, v=50.0, s=75.0)
      >>> row.total_value
      225.0
      >>> row.organic_composition  # c/v = 100/50
      2.0
      >>> row.exploitation_rate  # s/v = 75/50
      1.5

ValueTensor4x3
--------------

.. class:: ValueTensor4x3

   4x3 Marxian value tensor for a county-year.

   Represents the complete reproduction schema with four departments,
   each decomposed into constant capital (c), variable capital (v),
   and surplus value (s).

   **Fields:**

   .. attribute:: fips_code
      :type: str

      5-digit FIPS county code (e.g., "26163" for Wayne County, MI).
      Validated to be exactly 5 numeric digits.

   .. attribute:: year
      :type: int

      Data year. Must be >= 1900.

   .. attribute:: dept_I
      :type: DepartmentRow

      Department I: Means of Production (capital goods).
      Output consumed productively by capital.

   .. attribute:: dept_IIa
      :type: DepartmentRow

      Department IIa: Necessary Consumption (wage goods).
      Reproduces labor power.

   .. attribute:: dept_IIb
      :type: DepartmentRow

      Department IIb: Luxury Consumption (bourgeois goods).
      Absorbs surplus value without expanding reproduction.

   .. attribute:: dept_III
      :type: DepartmentRow

      Department III: Social Reproduction (care work).
      Maintains/creates workers outside commodity exchange.

   .. attribute:: naics_granularity
      :type: Probability

      Data quality metric: fraction of wages with 6-digit NAICS mapping.
      Range: [0.0, 1.0].

   .. attribute:: excluded_wages
      :type: Currency

      Wages excluded from allocation (e.g., government NAICS 92).

   .. attribute:: visibility_g33
      :type: float

      *Added in Sprint 2.1*

      Visibility scalar for Department III reproductive labor.
      Controls what fraction of care work is visible to the price system:

      - ``1.0``: Fully monetized (backward compatible default)
      - ``0.0``: Fully unwaged (all shadow labor)
      - ``0.5``: Half visible, half shadow

      Range: [0.0, 1.0]. Default: 1.0.

      Based on Fortunati's *The Arcane of Reproduction* (1981).

   **Computed Properties:**

   .. attribute:: total_value
      :type: Currency

      Sum of all department total_values.

   .. attribute:: total_v
      :type: Currency

      Total variable capital (wages) across all departments.

   .. attribute:: total_s
      :type: Currency

      *Added in Sprint 2.1*

      Total surplus value across all departments.

   .. attribute:: profit_rate
      :type: float

      Economy-wide return on capital: ``total_s / (total_c + total_v)``.
      Returns ``float('inf')`` if denominator is zero.

   .. attribute:: monetized_value
      :type: Currency

      *Added in Sprint 2.1*

      Total value visible to the price system. Includes full value of
      Depts I, IIa, IIb, but only the visible fraction of Dept III.

      Formula: ``Σ dept.total + dept_III.total × g₃₃``

   .. attribute:: monetized_v
      :type: Currency

      *Added in Sprint 2.1*

      Wages actually paid. Only includes the visible fraction of Dept III.

      Formula: ``v_I + v_IIa + v_IIb + (v_III × g₃₃)``

   .. attribute:: shadow_subsidy
      :type: Currency

      *Added in Sprint 2.1*

      Unpaid reproductive labor appropriated as surplus.

      Formula: ``v_III × (1 - g₃₃)``

      In Fortunati's framework, shadow labor is **appropriated surplus value**,
      not merely "unpaid costs".

   .. attribute:: exploitation_rate_fortunati
      :type: float

      *Added in Sprint 2.1*

      Expanded exploitation rate including shadow labor as appropriated surplus.

      Formula: ``e' = (total_s + shadow_subsidy) / monetized_v``

      Returns ``float('inf')`` when ``monetized_v = 0`` (pure extraction).

      See :ref:`reproductive-labor` for theoretical context.

   **Example:**

   .. code-block:: python

      >>> from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
      >>> tensor = ValueTensor4x3(
      ...     fips_code="26163",
      ...     year=2022,
      ...     dept_I=DepartmentRow(c=300.0, v=100.0, s=200.0),
      ...     dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
      ...     dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
      ...     dept_III=DepartmentRow(c=50.0, v=100.0, s=70.0),
      ...     naics_granularity=0.85,
      ...     excluded_wages=50000.0,
      ...     visibility_g33=0.5,
      ... )
      >>> tensor.profit_rate
      0.5826086956521739
      >>> tensor.shadow_subsidy  # 100 * (1 - 0.5)
      50.0
      >>> tensor.exploitation_rate_fortunati
      1.9428571428571428

The Four Departments
====================

.. list-table:: Marxian Departments
   :header-rows: 1
   :widths: 15 30 30 25

   * - Dept
     - Name
     - Purpose
     - Examples
   * - **I**
     - Means of Production
     - Output consumed productively by capital
     - Mining, Industrial Machinery, Semiconductors
   * - **IIa**
     - Necessary Consumption
     - Wage goods for proletariat reproduction
     - Grocery Stores, Fast Food, Basic Healthcare
   * - **IIb**
     - Luxury Consumption
     - Surplus value sink, bourgeois consumption
     - Jewelry Stores, Fine Dining, Golf Courses
   * - **III**
     - Social Reproduction
     - Produces labor power itself
     - Child Care, Private Households, K-12 Schools

Department III and Shadow Labor
-------------------------------

Department III is unique in containing **both** paid care work (visible to
markets) and unpaid domestic labor (invisible shadow subsidy). The visibility
scalar ``g₃₃`` controls this split.

Key insight from proletarian feminist theory: shadow labor is **necessary**
for capital accumulation but **invisible** to economic measurement.

The Infinity Case
=================

When ``monetized_v = 0``, the Fortunati exploitation rate returns ``float('inf')``.

This is **not** an edge case to be sanitized. It represents a **qualitative
transformation** from exploitation (wage relation) to expropriation (pure
extraction).

Historical conditions of infinite exploitation include:

- Chattel slavery
- Fully unwaged domestic labor
- Prison labor
- Colonial extraction

See :ref:`reproductive-labor` for full theoretical discussion.

Related Documentation
=====================

- :ref:`reproductive-labor` - Theoretical foundation
- :mod:`babylon.economics.hydrator` - Transforms QCEW data into tensors
- :mod:`babylon.economics.department_mapper` - Maps NAICS codes to departments
- ``ai-docs/marxian-tensor-spec.yaml`` - Machine-readable specification
- ``ai-docs/shadow-labor-spec.yaml`` - Shadow labor specification
