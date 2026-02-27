The NAICS Hierarchy and Double-Counting
========================================

QCEW data reports wages at every level of the NAICS classification
hierarchy. Summing across levels without filtering produces
catastrophic double-counting because parent codes *embed* all
children. This document explains the hierarchy structure, why
naive aggregation fails, and the rationale for leaf-only filtering.

.. contents:: On this page
   :local:
   :depth: 2

The Problem: Hierarchical Embedding
------------------------------------

The North American Industry Classification System (NAICS) organizes
industries into a strict hierarchy of increasing specificity:

- **2-digit** (sector): e.g., ``31-33`` = Manufacturing
- **3-digit** (subsector): e.g., ``336`` = Transportation Equipment
- **4-digit** (industry group): e.g., ``3361`` = Motor Vehicle Mfg
- **5-digit** (NAICS industry): e.g., ``33611`` = Automobile Mfg
- **6-digit** (national industry): e.g., ``336111`` = Automobile Mfg

Each parent level's reported wages *include all children's wages*.
Manufacturing (``31-33``) reports the sum of every 3-digit subsector,
which in turn sums every 4-digit group, and so on down to the
6-digit leaf codes. The hierarchy is not a set of independent
categories; it is a tree where each node's value equals the sum of
its descendants.

This means that if you sum wages across *all* hierarchy levels for
a county, you count every dollar of wages multiple times --- once at
each level it appears in. The multiplier depends on the depth of the
industry: a 6-digit code's wages appear at levels 6, 5, 4, 3, and 2
(five times), while a 2-digit code appears only once.

Empirical Evidence
~~~~~~~~~~~~~~~~~~~

Wayne County (FIPS 26163) in 2023:

- **Level 6 only**: $43.7 billion (correct)
- **All levels summed**: $454.7 billion (10.4x overcount)

The 10.4x factor reflects the average depth of the hierarchy weighted
by wage volume. Industries with deep classification trees (like
manufacturing) contribute more overcounting than shallow ones.

Why Simple Leaf Detection Fails
--------------------------------

The first instinct is to find "leaf nodes" --- NAICS codes with no
children in the database --- and sum only those. This approach
produces $111.1 billion for Wayne County, still 2.5x too high.
Three complications prevent it from working:

Compound Sector Codes
~~~~~~~~~~~~~~~~~~~~~~

NAICS uses three compound codes at the 2-digit level that span
multiple numeric ranges:

- ``31-33`` (Manufacturing)
- ``44-45`` (Retail Trade)
- ``48-49`` (Transportation and Warehousing)

These are *union* codes. ``31-33`` encompasses all codes from ``311``
through ``339``. The ``dim_industry`` table stores the literal string
``"31-33"`` as the ``naics_code``, with ``naics_level = 2``. A
simple parent-child check based on ``parent_naics_code`` does not
detect that ``311`` (Food Manufacturing) is a child of ``31-33``
because the string ``"311"`` does not start with ``"31-33"``.

BLS Supersector Codes
~~~~~~~~~~~~~~~~~~~~~~

The Bureau of Labor Statistics adds ``naics_level = 99`` codes
(e.g., ``1011`` through ``1029``) representing "supersectors" that
do not appear in the official NAICS taxonomy. These aggregate
multiple 2-digit sectors for BLS reporting convenience. Including
them adds another layer of duplication on top of the standard
hierarchy.

Incomplete Parent Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``dim_industry.parent_naics_code`` column does not universally
track all ancestry relationships. Some codes have ``NULL`` parents
even though they are clearly children of higher-level codes. This
makes tree-walking unreliable for leaf detection.

The Solution: Level 6 Filtering
--------------------------------

The correct approach filters to ``naics_level = 6`` (national
industry codes), which are the finest granularity in the standard
NAICS taxonomy. This eliminates all double-counting because:

1. Level 6 codes are the terminal leaves of the NAICS tree.
2. No level 6 code is a parent of any other level 6 code.
3. The union of all level 6 codes covers the same economic activity
   as any single higher-level code.

The ``SQLiteQCEWSource.fetch_county_wages()`` method applies this
filter:

.. code-block:: sql

   WHERE di.naics_level = 6

This produces county wage totals that match BLS published QCEW data
to within 92--99% accuracy. The remaining gap comes from government
employment (NAICS sector 92), which is not always reported at the
6-digit level.

The BEA Bridge Complication
----------------------------

The ``bridge_naics_bea`` table maps NAICS codes to BEA industry
categories. This mapping spans multiple NAICS hierarchy levels ---
some BEA industries map to 2-digit codes, others to 6-digit codes.
When aggregating national wages per BEA industry (for computing
Marxian ratios like *s/v* and *c/v*), the same hierarchical embedding
problem applies.

The ``InterpolatingBEASource`` handles this by loading the full
bridge table and filtering to leaf-only NAICS codes per BEA industry
using prefix-based ancestor detection:

1. Group all bridge mappings by ``bea_industry_id``.
2. For each BEA industry, collect the set of mapped NAICS codes.
3. A code is a "parent" if any other code in the set starts with
   its prefix (e.g., ``336`` is a parent of ``336111``).
4. Keep only non-parent codes (leaves within each BEA group).

Of the 466 total bridge mappings, 462 survive this filter. The four
removed are higher-level codes whose descendants are also mapped
individually.

Validation Against Published Data
----------------------------------

After applying leaf-only filtering, the Marxian hydrator produces
county-level wage totals that can be compared against BLS published
QCEW data:

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - County
     - Hydrator ($B)
     - BLS Published ($B)
     - Match
   * - Wayne (26163)
     - 41.2
     - 43.7
     - 94.3%
   * - Oakland (26125)
     - 49.5
     - 49.8
     - 99.4%
   * - Macomb (26099)
     - 17.9
     - 19.3
     - 92.8%

The 6--8% gaps are within expected range for data transformation and
filtering. The primary source of the gap is government wages (NAICS
sector 92), which BLS reports at aggregate levels but not always at
the 6-digit granularity.

With correct wage data, the tri-county metro profit rate (computed via
the MarxianHydrator pipeline) falls to 14.9% --- within the 3--15%
range documented in Piketty's historical analysis of advanced
economies. Before the fix, the pipeline reported 20.4% due to
inflated wage data producing distorted *s/v* and *c/v* ratios.

See Also
--------

- :doc:`economics-pipeline-theory` --- The full economics pipeline
  from value to class struggle
- :doc:`/reference/qcew-data` --- QCEW data schema and query
  reference
- :doc:`/reference/bea-department-mapping` --- BEA industry to
  Marxian department classification
- :doc:`piketty-profit-rate` --- Historical profit rate bounds
