.. _leontief-analysis:

====================================================
Input-Output Economics and the Leontief Inverse
====================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

The Leontief inverse is the mathematical core of Babylon's
``DefaultLeontiefComputer``. This document explains what input-output (I-O)
tables measure, the economic conditions under which they can be inverted, and
what the resulting matrix means.

For the complete API reference, see :ref:`tensor-hierarchy-reference`.

----

What Input-Output Tables Measure
=================================

A BEA Input-Output Use table captures the *direct* intermediate requirements
of every industry. Entry *A*\[*i*,*j*] answers the question:

  *How many dollars of commodity i does industry j require to produce one
  dollar of its own output?*

For example, if the chemical industry (*j*) requires $0.12 of petroleum
products (*i*) per dollar of chemical output, then *A*\[petroleum, chemicals]
= 0.12. This is the **direct requirements coefficient**.

The full matrix *A* is square: *n* industries × *n* industries (about 70 at
BEA Summary level). Column *j* describes the complete input basket of industry
*j*—everything it buys from other industries per dollar of output.

The BEA I-O Use Table Structure
---------------------------------

The raw Use table contains dollar values in millions. The coefficient matrix
*A* is derived by normalizing each column by its industry's gross output:

.. math::

   A_{ij} = \frac{\text{Use}_{ij}}{\text{GrossOutput}_j}

where Use\ :sub:`ij` is the dollar value of commodity *i* used by industry *j*,
and GrossOutput\ :sub:`j` is the total output of industry *j* (from BEA row
T019, or approximated as intermediate use plus value added when T019 is absent).

Missing data in the BEA XLSX (marked ``'...'``) is treated as zero. This is
conservative: it understates inter-industry linkages in sectors with incomplete
survey coverage.

----

The Hawkins-Simon Condition
============================

For the economy to be *productive*—capable of producing net output rather than
being consumed entirely by its own intermediate requirements—the input-output
matrix must satisfy the **Hawkins-Simon condition**:

.. math::

   \text{All column sums of } A < 1.0

This means each industry's total intermediate input purchases, as a fraction
of its gross output, must be less than one. If a column sum equals or exceeds
1.0, that industry consumes at least as much as it produces in intermediate
inputs—a non-productive economy.

Babylon's validation tier implements this condition:

.. list-table:: I-O Column Sum Validation Thresholds
   :header-rows: 1
   :widths: 20 20 60

   * - Threshold
     - Value
     - Meaning
   * - Expected max
     - 0.90
     - Normal productive economy; typical US sector column sums
   * - Warning max
     - 0.99
     - Near-singular; data quality issues possible
   * - Fail (invalid)
     - 1.00
     - Violates Hawkins-Simon; (I − A) is not invertible

The Perron-Frobenius theorem guarantees that when the Hawkins-Simon condition
holds, the Leontief inverse *L* = (*I* − *A*)\ :sup:`−1` exists and has all
non-negative elements.

----

The Leontief Inverse
=====================

The direct requirements matrix *A* captures only first-order supplier
relationships. But every supplier also has suppliers. Steel requires iron ore
mining, which requires mining machinery, which requires steel. These indirect
requirements are what the Leontief inverse captures.

The inverse *L* = (*I* − *A*)\ :sup:`−1` can be understood via the geometric
series expansion:

.. math::

   L = I + A + A^2 + A^3 + \cdots

Each power *A*\ :sup:`k` represents requirements *k* steps up the supply chain.
The sum converges when the Hawkins-Simon condition holds (spectral radius of
*A* < 1).

What *L*\[*i*,*j*] Means
--------------------------

The element *L*\[*i*,*j*] answers:

  *How much total output of industry i is required (directly and indirectly
  through all supply chain tiers) to deliver one dollar of final demand
  for industry j?*

Several mathematical properties follow necessarily:

**All elements non-negative.** Since a productive economy cannot require
negative output from any sector to satisfy positive final demand.

**Diagonal elements ≥ 1.0.** Industry *j* requires at least one dollar of its
own output to produce one dollar for final demand (it needs itself as input, at
minimum directly). Diagonal values exceed 1.0 by the amount of self-use plus
the indirect self-requirements embodied in upstream supply chains.

**Column sums > 1.0.** Total production requirements across all industries
exceed the final demand satisfied, because every unit of final demand requires
additional intermediate production throughout the economy.

These are not assumptions—they are mathematical consequences of the Hawkins-
Simon condition. Babylon's validation checks all three:

.. list-table:: Leontief Inverse Validation Rules
   :header-rows: 1
   :widths: 35 65

   * - Property
     - Enforcement
   * - All elements ≥ 0
     - Fail if any element < −1e-10 (small tolerance for floating-point noise)
   * - Diagonal ≥ 1.0
     - Fail if any diagonal element < 1.0 − 1e-10

----

Total Labor Coefficients
=========================

One of the most useful applications of the Leontief inverse is computing
**total labor requirements**: the total labor (direct plus all indirect) needed
per unit of final demand.

Given a vector *l*\ :sub:`direct` where *l*\ :sub:`direct`\[*j*] = direct labor
hours per dollar of industry *j*'s gross output:

.. math::

   l_{\text{total}} = l_{\text{direct}} \cdot L

Each element *l*\ :sub:`total`\[*j*] is the total economy-wide labor hours
required per dollar of final demand for industry *j*, including all upstream
supply chains. This quantity is essential for:

- Computing Marxian values (labor embodied in commodities)
- Identifying labor-intensive versus capital-intensive sectors
- Measuring the real labor content of final consumption bundles by class

The computation is a single matrix-vector multiply:
``l_total = l_direct @ leontief.inverse_matrix``.

----

Department Aggregation: From 70 to 4
=======================================

The BEA Summary table has ~70 industries. Marxian analysis requires 4
departments. The ``DefaultDepartmentAggregator`` performs this reduction using
a TOML-defined mapping from BEA codes to departments.

The Aggregation Method
-----------------------

Aggregating an I-O matrix is not as simple as summing rows and columns. Each
department contains industries with different output scales, and the
within-department coefficients must be weighted correctly.

Babylon uses **output-share weighting**: each industry's contribution to its
department's column is proportional to its share of total intermediate purchases
(column sum of *A* relative to total). The algorithm:

1. Assign each industry to a department via the TOML mapping.
2. Compute column-sum weights (output shares) for each industry.
3. For each (source department, target department) pair, compute the
   weighted average coefficient across all industry pairs that map to
   that department combination.
4. Re-normalize to ensure the resulting 4×4 matrix preserves the row
   structure of the original.

What We Gain and Lose
-----------------------

**Gain:** The 4×4 matrix is directly interpretable in Marxian terms. It shows
how much of Department I's output goes to Department IIa as direct input (means
of production used in wage-goods production), and so on. These are precisely the
inter-department flows in Marx's expanded reproduction schemas in *Capital
Volume II*.

**Lose:** Within-department heterogeneity disappears. The 70 industries in
Department I are not identical—mining has a different capital structure than
financial services. The 4×4 matrix represents only an average of these
differences, weighted by output shares.

For most simulation purposes, the 4-department aggregation is sufficiently
precise. For detailed sector-level analysis, the full 70×70 matrix via
``InterIndustryFlow`` and ``LeontiefInverse`` is available.

----

Historical Context
==================

Wassily Leontief developed input-output analysis in the 1930s–1940s, for
which he received the 1973 Nobel Prize in Economics. The method operationalizes
Marx's reproduction schemas from *Capital Volume II* (1885): Marx's
qualitative insight that departments must balance in expanded reproduction
becomes quantifiable via the I-O matrix.

Leontief himself worked on what he called "structural economic analysis"—the
same project that Babylon pursues, but applied to the contradictions of
American capitalism specifically. His 1953 discovery that US exports were more
labor-intensive than imports (the "Leontief paradox") anticipated world-systems
theory's insight that core-periphery trade involves unequal exchange of labor.

----

Related Documentation
=====================

- :ref:`tensor-hierarchy-concept` — Three-level tensor architecture overview
- :ref:`imperial-rent-field` — Spatial value extraction via geographic flows
- :ref:`bea-io-tables` — BEA I-O data format, file inventory, and loader API
- :ref:`bea-department-mapping` — Full BEA-to-Marxian department mapping
- :ref:`tensor-hierarchy-reference` — Complete API and data dictionary
- :mod:`babylon.economics.tensor_hierarchy.inter_industry` — Implementation
