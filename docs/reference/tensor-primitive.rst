Fundamental Tensor Primitive Reference
======================================

Technical reference for the ValueTensor4x3 — the single source of
truth for all economic data in the Babylon simulation. All values are
measured in labor-hours, not monetary units. The tensor layer is the
only component that queries the database for economic data.

.. contents:: On this page
   :local:
   :depth: 2

Core Data Types
---------------

NoDataSentinel
~~~~~~~~~~~~~~

Non-instantiable falsy marker for missing tensor data. Enables the
walrus operator pattern:

.. code-block:: python

   if tensor := registry.get("26163", 2020):
       print(tensor.exploitation_rate)
   else:
       print(tensor.reason)  # "FIPS code not in database"

.. list-table:: NoDataSentinel Fields
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``fips``
     - ``str``
     - 5-digit county FIPS code
   * - ``year``
     - ``int``
     - Calendar year
   * - ``reason``
     - ``str``
     - Human-readable error (format: ``"{context}: {reason}"``)

``bool(sentinel)`` returns ``False``. Implements ``__eq__`` and
``__hash__`` for use in dicts and sets.

DepartmentRow
~~~~~~~~~~~~~

Value composition for a single Marxian department. Frozen Pydantic
model with three non-negative ``LaborHours`` fields.

.. list-table:: DepartmentRow Fields
   :header-rows: 1
   :widths: 15 15 70

   * - Field
     - Type
     - Description
   * - ``c``
     - ``LaborHours``
     - Constant capital (dead labor / means of production consumed)
   * - ``v``
     - ``LaborHours``
     - Variable capital (living labor / wages paid)
   * - ``s``
     - ``LaborHours``
     - Surplus value (unpaid labor appropriated by capital)

**Computed properties:**

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Property
     - Formula
     - Note
   * - ``total_value``
     - c + v + s
     - Total commodity value
   * - ``organic_composition``
     - c / v
     - Capital intensity (``inf`` if v = 0)
   * - ``exploitation_rate``
     - s / v
     - Unpaid labor ratio (``inf`` if v = 0)

ValueTensor4x3
~~~~~~~~~~~~~~

The fundamental 4×3 Marxian reproduction schema for a county-year.
Frozen Pydantic model with index structure
``T^μ_ν[fips, year]`` where μ ∈ {I, IIa, IIb, III}
and ν ∈ {c, v, s}.

.. list-table:: ValueTensor4x3 Fields
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``fips_code``
     - ``str[5]``
     - County FIPS code (regex validated)
   * - ``year``
     - ``int >= 1900``
     - Calendar year
   * - ``dept_I``
     - ``DepartmentRow``
     - Means of production (capital goods)
   * - ``dept_IIa``
     - ``DepartmentRow``
     - Necessary consumption (wage goods)
   * - ``dept_IIb``
     - ``DepartmentRow``
     - Luxury consumption (bourgeois goods)
   * - ``dept_III``
     - ``DepartmentRow``
     - Social reproduction (care work)
   * - ``naics_granularity``
     - ``Probability``
     - Data quality: fraction of wages with 6-digit NAICS
   * - ``excluded_wages``
     - ``LaborHours``
     - Government/excluded sector wages (outside M-C-M')
   * - ``visibility_g33``
     - ``float [0, 1]``
     - Visibility of care work to price system (Fortunati)

Departments
~~~~~~~~~~~

.. list-table:: Four Marxian Departments
   :header-rows: 1
   :widths: 15 30 55

   * - Code
     - Name
     - Description
   * - I
     - Means of Production
     - Capital goods: machinery, raw materials, infrastructure
   * - IIa
     - Necessary Consumption
     - Wage goods: food, housing, transport for workers
   * - IIb
     - Luxury Consumption
     - Bourgeois goods: luxury housing, yachts, art
   * - III
     - Social Reproduction
     - Care work: childcare, cooking, eldercare, emotional labor

Computed Metrics
----------------

Aggregate Metrics
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Property
     - Formula
     - Description
   * - ``total_value``
     - Σ dept.total_value
     - Total commodity value across all departments
   * - ``total_c``
     - Σ dept.c
     - Total constant capital
   * - ``total_v``
     - Σ dept.v
     - Total variable capital (total wages in labor-hours)
   * - ``total_s``
     - Σ dept.s
     - Total surplus value

Rate Metrics
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Property
     - Formula
     - Description
   * - ``profit_rate``
     - s / (c + v)
     - Economy-wide return on capital (r)
   * - ``exploitation_rate``
     - s / v
     - Rate of surplus value extraction (e)
   * - ``organic_composition``
     - c / v
     - Capital intensity (OCC)

Imperial Rent
~~~~~~~~~~~~~

.. math::

   \Phi = v - (c + v + s)

Positive Φ: core territory receives imperial rent (labor aristocracy).
Negative Φ: periphery territory donates value.

Fortunati Visibility Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The visibility scalar *g₃₃* controls what fraction of Department III
(reproductive labor) the price system recognizes:

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Property
     - Formula
     - Description
   * - ``monetized_value``
     - Σ(I,IIa,IIb) + III × g₃₃
     - Value visible to price system
   * - ``monetized_v``
     - Σ(I,IIa,IIb).v + III.v × g₃₃
     - Wages actually paid
   * - ``shadow_subsidy``
     - III.v × (1 − g₃₃)
     - Unpaid reproductive labor
   * - ``exploitation_rate_fortunati``
     - (s + shadow) / monetized_v
     - True exploitation including care work

When g₃₃ = 1.0, all care work is monetized (no shadow subsidy).
When g₃₃ = 0.0, all care work is invisible (maximum shadow
extraction).

Tensor Registry
---------------

:py:class:`babylon.economics.tensor_registry.TensorRegistry` is the
cache and aggregation layer that provides tensor access to the
simulation engine.

Access Methods
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Description
   * - ``get(fips, year)``
     - County tensor (cache hit, no DB). Returns NoDataSentinel if missing.
   * - ``get_aggregate(level, code, year)``
     - Aggregated tensor (lazy compute, LRU cached)
   * - ``put(fips, year, tensor)``
     - Store tensor, invalidate aggregate cache
   * - ``put_sentinel(fips, year, reason)``
     - Mark (fips, year) as explicitly missing
   * - ``hydrate_counties(hydrator, fips_codes, years)``
     - Bulk load via external hydrator
   * - ``all_fips()``
     - frozenset of cached FIPS codes
   * - ``available_years(fips)``
     - frozenset of years for a county

Geographic Aggregation
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: GeoLevel Enum
   :header-rows: 1
   :widths: 15 25 60

   * - Level
     - Code Format
     - Description
   * - COUNTY
     - 5-digit FIPS
     - Individual county (direct cache lookup)
   * - STATE
     - 2-digit FIPS
     - Sum all counties with matching state prefix
   * - NATION
     - ``"US"``
     - Sum all available counties

Aggregation sums department values. ``naics_granularity`` and
``visibility_g33`` are weighted averages by ``total_value``.

Performance
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Operation
     - Target
     - Note
   * - ``get()`` cache hit
     - < 1ms p95
     - Direct dict lookup
   * - ``get_aggregate()`` warm
     - < 1ms p95
     - LRU cache hit
   * - ``get_aggregate()`` cold
     - < 100ms p95
     - Computed, then cached
   * - Peak RSS (full US)
     - < 500MB
     - LRU eviction at threshold

Thread-safe via RLock on both county and aggregate caches.

Hydration Pipeline
------------------

:py:class:`babylon.economics.hydrator.MarxianHydrator` transforms
raw QCEW wage data into ValueTensor4x3 using BEA ratios and
department mappings.

Pipeline Steps
~~~~~~~~~~~~~~

1. **Fetch QCEW records**: ``[(naics_code, total_wages, employment)]``
   via ``QCEWDataSource.fetch_county_wages(fips, year)``

2. **Get SNLT factor**: Year-specific conversion factor (default 1.0 =
   wage-proportional proxy)

3. **Allocate to departments**: ``DepartmentMapper.allocate_batch()``
   distributes wages across I/IIa/IIb/III by NAICS-to-department
   weights. Excluded sectors (NAICS 92 = government) tracked as
   ``excluded_wages``.

4. **Apply BEA ratios per department**:

   .. math::

      s = v \times \frac{s}{v}_{\text{ratio}}
      \qquad
      c = v \times \frac{c}{v}_{\text{ratio}}

5. **Convert to labor-hours**: Multiply by SNLT factor

6. **Compute naics_granularity**: (6-digit wages) / (allocated wages)

7. **Return frozen ValueTensor4x3**

Ratio Lookup Hierarchy
~~~~~~~~~~~~~~~~~~~~~~

For both s/v and c/v ratios, the system tries three sources
(most specific first):

1. **BEA source** — empirical industry-level data from
   ``fact_bea_national_industry`` with temporal interpolation
   (nearest year within ±5 years)
2. **Sector YAML** — 2-digit NAICS ratios from
   ``naics_to_dept.yaml``
3. **Department default** — fallback per department (e.g.,
   Dept I default c/v = 2.0, s/v = 1.5)

SNLT Configuration
~~~~~~~~~~~~~~~~~~

:py:class:`babylon.economics.snlt.SNLTConfig` provides year-specific
labor-hour conversion factors.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Factor
     - Meaning
   * - 1.0
     - Wage-proportional proxy (derived ratios exact, magnitudes
       uncalibrated)
   * - < 1.0
     - Higher productivity (fewer labor-hours per dollar)
   * - > 1.0
     - Lower productivity (more labor-hours per dollar)

Until SNLT calibration is complete, the default factor of 1.0
means tensor values are *wage-proportional labor-time proxies*.
All derived ratios (r, e, OCC) are exact; absolute magnitudes
require SNLT calibration.

Department Mapping
~~~~~~~~~~~~~~~~~~

:py:class:`babylon.economics.department_mapper.DepartmentMapper`
maps NAICS codes to departments with allocation weights.

**NAICS lookup hierarchy** (most specific first):

1. 6-digit override (e.g., ``325110`` → specific chemical)
2. 5, 4, 3-digit overrides
3. 2-digit sector default (e.g., ``44`` → Retail)
4. Excluded set (NAICS ``92`` = government, outside M-C-M')

**Allocation weights** sum to 1.0 per NAICS code. Example:

- Agriculture (``11``): 62% Dept I, 33% Dept IIa, 5% Dept IIb
- Wholesale (``42``): 85% Dept I, 15% Dept IIa
- Retail (``44``): 72% Dept IIa, 28% Dept IIb

Configured via ``naics_to_dept.yaml``.

Data Source Protocols
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Protocol
     - Method
   * - ``QCEWDataSource``
     - ``fetch_county_wages(fips, year)``
       → ``list[(naics, wages, employment)]``
   * - ``BEADataSource``
     - ``get_sv_ratio(naics, year)`` → ``float | None``
       ``get_cv_ratio(naics, year)`` → ``float | None``
   * - ``CountyHydrator``
     - ``hydrate(fips, year)`` → ``ValueTensor4x3``

**Implementations:**

- ``SQLiteQCEWSource``: Queries ``fact_qcew_annual`` via 3NF joins
- ``InterpolatingBEASource``: Queries ``fact_bea_national_industry``
  with linear temporal interpolation (±5 years)

See Also
--------

- :doc:`/concepts/tensor-theory` — Theoretical exposition of the
  Marxian value tensor
- :doc:`/reference/formulas` — Complete formula reference
- :doc:`/reference/volume-i-production` — How Volume I mechanisms
  modify tensor values
- :doc:`/reference/data-models` — Full data model reference
