.. _imperial-rent-field:

====================================================
The Imperial Rent Field: Spatial Value Extraction
====================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

The imperial rent field (φ) operationalizes world-systems theory's core claim:
that value systematically flows from geographic periphery to core through the
mechanism of commodity exchange. This document explains how BTS FAF5 freight
data serves as a proxy for these value flows, the mathematics of the symmetric/
antisymmetric decomposition, and the limitations of the approach.

For the API reference, see :ref:`tensor-hierarchy-reference`.
For the data format reference, see :ref:`faf-freight-data`.

----

Commodity Flows as Value Flows
================================

The fundamental challenge in measuring imperial rent at the domestic level is
that *value* (in the Marxist sense: socially necessary abstract labor time) is
not directly observable in national accounts. What is observable is *price*—
and price deviates from value through the mechanisms of unequal exchange,
monopoly pricing, and differential wages.

Babylon uses **USD freight value from the BTS Freight Analysis Framework
(FAF5)** as an approximation of value flows. The approximation rests on the
**social necessary labor time (SNLT) assumption**: over the full circuit of
capital, deviations between price and value average out, and commodity prices
are proportional to the labor embodied in production.

This is an approximation, not a precise measurement. The limitations section
below addresses where this assumption breaks down most severely. The key
insight is that freight flow data provides the *structure* of inter-regional
economic relationships—which areas are net exporters of value, which are net
importers—even if the exact magnitudes require further adjustment.

Scale of the Data
------------------

The FAF5 2022 data covers:

- **$18.7 trillion** in domestic commodity shipments (USD value)
- **2.49 million** origin-destination flow records (before aggregation)
- **~130 CFS Areas** (Census Commodity Flow Survey geographic zones)
- **42 SCTG commodity codes** (Standard Classification of Transported Goods)
- **5 transport modes** (truck, rail, water, air, pipeline)

CFS Areas are aggregations of counties used by the Census Bureau for freight
analysis. They are larger than individual counties but smaller than states,
providing a geographically intermediate resolution appropriate for
regional value flow analysis.

----

The Flow Matrix
================

The origin-destination flow matrix *F* is a 130×130 array where:

.. math::

   F[a, b] = \text{USD value (millions) of freight shipped from CFS Area } a
              \text{ to CFS Area } b

The matrix is not symmetric. More freight flows from agricultural Midwest areas
to coastal consumer markets than in reverse. These asymmetries reveal the
directional structure of value flows.

From the Flow Matrix to the Imperial Rent Field
-------------------------------------------------

For each CFS Area *a*, define:

.. math::

   \phi[a] = \text{inflow}[a] - \text{outflow}[a]

where:

.. math::

   \text{inflow}[a] = \sum_b F[b, a] \quad \text{(column sum: all areas sending to } a\text{)}

.. math::

   \text{outflow}[a] = \sum_b F[a, b] \quad \text{(row sum: all areas receiving from } a\text{)}

Areas with **positive φ** receive more commodity value than they ship—they
are net value importers, which in world-systems theory identifies them as
**core accumulation zones**.

Areas with **negative φ** ship more commodity value than they receive—they
are net value exporters, which identifies them as **periphery extraction zones**.

Conservation Property
-----------------------

For a closed domestic system, the sum of all imperial rent values must be zero:

.. math::

   \sum_a \phi[a] = \sum_a \text{inflow}[a] - \sum_a \text{outflow}[a] = 0

(Every outflow from one area is an inflow to another.) In practice, small
numerical deviations arise from floating-point arithmetic. Babylon validates
conservation at three tiers:

.. list-table:: Imperial Rent Conservation Validation
   :header-rows: 1
   :widths: 20 20 60

   * - Tier
     - Threshold
     - Meaning
   * - Expected
     - \|Σφ\| < 0.01% of total flow
     - Excellent conservation; numerical precision
   * - Warning
     - \|Σφ\| < 0.1% of total flow
     - Acceptable; possible rounding from integer data
   * - Fail
     - \|Σφ\| ≥ 1% of total flow
     - Data error; conservation violated

----

Symmetric and Antisymmetric Decomposition
==========================================

The flow matrix *F* can be decomposed into two components with distinct
economic interpretations:

.. math::

   F = S + A

where:

.. math::

   S = \frac{F + F^T}{2} \quad \text{(symmetric component: bilateral exchange)}

.. math::

   A = \frac{F - F^T}{2} \quad \text{(antisymmetric component: net directional flow)}

The Symmetric Component *S*
-----------------------------

*S*\[*a*,*b*] = *S*\[*b*,*a*] represents the **bilateral exchange** between
areas *a* and *b*—the average of what each sends to the other. This captures
genuine two-way trade relationships: area *a* sends manufactured goods to
area *b*, which sends agricultural goods back. The symmetric component
represents *reciprocal* commodity exchange.

The Antisymmetric Component *A*
--------------------------------

*A*\[*a*,*b*] = −*A*\[*b*,*a*] represents the **net directional flow**:
if *A*\[*a*,*b*] > 0, area *a* is a net exporter to area *b*. This is the
component that encodes unequal exchange—the directional bias in flows that
causes value to accumulate in some areas and drain from others.

Crucially, the imperial rent field φ is entirely determined by the antisymmetric
component:

.. math::

   \phi[a] = \sum_b A[b, a] - \sum_b A[a, b] = 2 \sum_b A[b, a]

The symmetric component contributes nothing to φ because its contributions
cancel. This means the imperial rent field measures *only* the net directional
structure, not the bilateral exchange volume.

----

Theoretical Grounding
======================

The imperial rent field operationalizes three overlapping theoretical
traditions:

Samir Amin — Unequal Exchange
-------------------------------

Amin (*Unequal Development*, 1976) argues that the international division of
labor systematically transfers value from peripheral to core nations through
the price mechanism. Wages in the periphery are below the value of labor power;
wages in the core exceed it. The price of peripheral exports therefore embeds
more labor than is compensated, constituting a transfer of value.

Applied domestically, the same logic identifies regions where labor is
underpaid relative to the value embodied in exports (resource extraction
regions, agricultural zones) as peripheral, and regions where labor is
overpaid relative to value (financial centers, tech hubs) as core.

Immanuel Wallerstein — World-Systems Theory
---------------------------------------------

World-systems theory (*The Modern World-System*, 1974) describes a core-
periphery-semiperiphery structure that maintains itself through unequal
exchange and political enforcement. The structure is not static—regions can
move between positions over historical time.

The FAF-derived imperial rent field provides a snapshot of this structure at
the domestic (CFS Area) level, revealing which American regions are
functionally peripheral within the national economy.

MLM-TW — Imperial Rent (Φ)
----------------------------

Babylon's broader theoretical framework uses Imperial Rent (Φ = *W*\ :sub:`c`
− *V*\ :sub:`c`) to explain why revolution in the core is structurally
impossible: core workers receive wages above the value they produce, funded by
value extracted from the periphery. The geographic flow tensor makes this
spatial extraction computable at the CFS Area level.

The connection to the simulation engine is direct: CFS Area φ values can be
aggregated to county level via the ``bridge_cfs_county`` junction table, and
then used to calibrate or validate the ``ImperialRentSystem``'s extraction
calculations at the county grain.

----

Limitations of the Approach
============================

**Freight only, not services.** FAF5 captures physical commodity shipments.
Financial services, intellectual property, and other intangible value flows—
which constitute a large share of value transfer in the modern economy—are
entirely absent. This understates the core's extraction from the periphery
because financial rent tends to flow toward core areas.

**Domestic flows only.** FAF5 covers domestic US freight. International value
flows (the classic subject of unequal exchange theory) are outside scope.
The imperial rent field measures *intra-US* spatial value extraction.

**Price ≠ Value.** The SNLT approximation is weakest where monopoly pricing
is strongest (pharmaceuticals, digital goods, financial derivatives) and
where wage differentials are largest (farm labor vs. financial sector). The
freight value figures embed these distortions.

**Annual snapshot.** FAF5 provides annual estimates, not real-time flows.
The computed φ vector is a structural average, not a dynamic measure of
ongoing value transfer.

Despite these limitations, the geographic flow tensor provides the closest
available empirical approximation to spatial imperial rent extraction at the
regional level.

----

Related Documentation
=====================

- :ref:`tensor-hierarchy-concept` — Three-level tensor hierarchy overview
- :ref:`leontief-analysis` — Leontief I-O inverse theory
- :ref:`faf-freight-data` — BTS FAF5 data format, file inventory, and loader API
- :ref:`tensor-hierarchy-reference` — Complete tensor and protocol data dictionary
- :ref:`tensor-hierarchy-schema` — SQLite table definitions
- :mod:`babylon.domain.economics.tensor_hierarchy.geographic_flow` — Implementation
- :doc:`imperial-rent` — The broader MLM-TW imperial rent concept (Φ = W\ :sub:`c` − V\ :sub:`c`)
