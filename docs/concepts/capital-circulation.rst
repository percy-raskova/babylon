Capital Volume II: The Circulation of Capital
==============================================

Marx's *Capital Volume II* (1885) analyzes the **circulation** of capital
-- the movement of value through its metamorphoses and the conditions for
its reproduction. This document explains the theoretical reasoning behind
Babylon's Volume II implementation and why these dynamics matter for the
simulation.

.. contents:: On this page
   :local:
   :depth: 2

Why Volume II Matters for the Simulation
----------------------------------------

Babylon already models two of capital's three faces:

- **Volume I** (Features 011-021): How surplus value is *produced* --
  the extraction of unpaid labor at the point of production. The
  ValueTensor4x3 captures the composition (c, v, s) and the reserve
  army / dispossession / working day mechanics explain *why* those
  values change.

- **Volume III** (Feature 018): How surplus value is *distributed* --
  the tendency of the rate of profit to fall and the crisis dynamics
  that follow from it.

Volume II fills the gap between production and distribution: How does
surplus value *move*? Capital is not a thing sitting in an account. It
is a process -- a continuous flow of value through different forms. The
simulation needed to know:

1. **How long** does capital take to complete a circuit? (turnover time)
2. **What form** is capital currently in? (money, productive, commodity)
3. **Can departments exchange proportionally** for reproduction to
   continue? (reproduction schema)
4. **Can produced commodities actually be sold?** (realization)

Without these, the simulation describes a snapshot. With them, it
describes a motion picture.

Capital as Process: The M-C-P-C'-M' Circuit
--------------------------------------------

The central insight of Volume II is that capital exists simultaneously
in three forms, cycling continuously::

    M  →  C{LP, MP}  ...  P  ...  C'  →  M'

**Money capital** (M) exists as liquidity -- cash, deposits, receivables.
It purchases labor power (LP) and means of production (MP), transforming
into **productive capital** (P). Production transforms inputs into
outputs with surplus value embodied, yielding **commodity capital** (C').
Sale of commodities realizes the surplus, returning value to money form
(M' = M + surplus).

Three perspectives reveal different dynamics:

**The money circuit** (M → C ... P ... C' → M') emphasizes
valorization -- capital goes in as money, comes out as more money.
This is the perspective of the investor.

**The productive circuit** (P ... C' → M' → C ... P) emphasizes
continuity -- production must be sustained without interruption.
This is the perspective of the factory.

**The commodity circuit** (C' → M' → C ... P ... C') emphasizes
realization -- commodities must find buyers. This is the perspective
that reveals crisis: what happens when they cannot be sold?

In Babylon, each county's capital is distributed across all three
forms simultaneously. The ``CircuitState`` tracks this distribution
and its ``liquidity_ratio`` and ``commodity_overhang`` computed fields
serve as real-time diagnostic indicators.

Turnover Time: Why Speed Matters
--------------------------------

A crucial Volume II discovery: **faster turnover increases the annual
rate of surplus value** even with the same rate of exploitation per cycle.

Consider two capitals, both with s/v = 100% (the worker produces as
much surplus as they receive in wages):

- Capital A turns over every 2 months (6 times per year).
  Annual rate of surplus value = 100% x 6 = **600%**.

- Capital B turns over every 6 months (2 times per year).
  Annual rate of surplus value = 100% x 2 = **200%**.

Same exploitation rate. Triple the annual surplus. This is why capitalism
relentlessly accelerates: faster turnover = more surplus from the same
capital advanced. Amazon's logistics revolution is not just about customer
convenience -- it is about compressing turnover time to extract more
surplus per year from the same variable capital.

Turnover time decomposes into two phases:

**Production time** = working period + non-working production time.
The working period is when labor actually transforms materials.
Non-working production time is when capital sits in production
without labor -- fermentation, drying, aging. Marx's example:
American shoe-last manufacturing required 18 months of wood drying
before any labor could begin.

**Circulation time** = purchase time + sale time. Purchase time
(M → C) is how long it takes to acquire inputs. Sale time (C' → M')
is how long it takes to find buyers. In the simulation, sale time
is the critical variable -- a county with better market access has
shorter sale times, faster turnover, and higher annual surplus.

Fixed vs Circulating Capital
----------------------------

Volume II introduces a second decomposition of capital that cuts
across the Volume I distinction:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - Constant (c)
     - Variable (v)
   * - **Fixed**
     - Machinery, buildings
     - --
   * - **Circulating**
     - Raw materials, fuel
     - Wages

This is NOT the same as constant vs variable capital. The distinction
is about **mode of turnover**: fixed capital transfers value gradually
through depreciation. Circulating capital transfers value completely
each production cycle. Variable capital (wages) is always circulating
-- labor power is fully consumed each cycle.

This creates the **depreciation fund problem**: value transfers
continuously (each production cycle takes a fraction of the machine's
value), but replacement happens discretely (when the machine wears out).
The accumulated depreciation fund is **latent money capital** -- sitting
idle, waiting for replacement. This idle capital is a material basis
for the credit system and business cycles.

Marx also emphasized **moral depreciation** -- machinery becomes
obsolete not because it wears out but because better machinery exists.
The ``MoralDepreciation`` model tracks the ratio of economic remaining
life to physical remaining life. When this ratio drops below 1.0,
the machine is economically dead before it is physically dead.

The Reproduction Schema
-----------------------

Volume II's most famous contribution is the reproduction schema --
the conditions under which the economy can reproduce itself.

**Simple reproduction** requires that Department I's output of
consumption goods (wages + surplus spent on consumption) equals
Department II's demand for means of production::

    I(v + s) = IIc

If Department I produces more than Department II needs, there is
overproduction of means of production. If less, underproduction.
Either imbalance means the economy cannot reproduce at the same scale.

**Extended reproduction** (accumulation) requires that surplus is
partly reinvested: s = s_consumed + s_accumulated, where
s_accumulated = delta_c + delta_v. The accumulation rate determines
the growth trajectory.

Babylon adds **Department III** (reproductive labor) to the schema.
The extended reproduction check compares total labor power demand
(sum of all departments' v) against Department III's reproduction
capacity (III's c + v + s). When demand exceeds capacity, the system
flags exploitation of reproductive labor -- the hidden subsidy that
sustains accumulation.

This connects directly to the ``visibility_g33`` parameter from the
value tensor. When reproductive labor is invisible (g33 → 0), the
reproduction gap is hidden. As visibility rises, the gap between what
the economy demands from reproductive workers and what it provides
them becomes legible.

Realization Crisis
------------------

Volume II reveals crisis tendencies distinct from the tendency of the
rate of profit to fall (TRPF):

**Realization crisis**: Commodities are produced but cannot be sold.
C' → M' fails. The ``RealizationCrisis`` model tracks the gap between
value produced and value realized. When the realization rate drops
below 70%, the system classifies it as a full crisis.

**Disproportionality crisis**: Departments produce at incompatible
ratios. Department I produces more means of production than Department
II can absorb, or vice versa. The economy's internal structure is
out of balance.

**Turnover disruption**: The circuit itself is interrupted. Working
capital is insufficient to continue production. In the model, this
manifests as liquidity ratio below 10% combined with circulation time
exceeding production time -- capital is stuck in circulation, unable
to return to production.

These three crisis types are **independent of TRPF**. A county can
have a stable profit rate but face realization crisis (overproduction),
disproportionality (structural imbalance), or turnover disruption
(liquidity crisis). In Babylon, the ``CirculationCrisisAssessment``
runs alongside the existing ``CrisisState`` from Feature 018. Both
signals are available to downstream consumers.

Circulation Costs: Productive vs Unproductive Labor
---------------------------------------------------

Volume II draws a line between labor that creates value and labor that
merely facilitates its exchange:

**Productive labor** transforms materials or changes location. A factory
worker adds value by transforming raw materials into products. A truck
driver adds value by changing a commodity's location -- transportation
is "production continued in circulation." The ``TransportationValue``
model captures the c + v + s that transport adds to commodity value.

**Unproductive labor** facilitates exchange without creating value.
Salespeople, accountants, advertising creatives, security guards --
these are necessary for capitalism but do not add to the total value
produced. They are a deduction from surplus. The ``PureCirculationCosts``
model tracks these faux frais and computes the ``circulation_burden``
-- what fraction of revenue goes to pure circulation.

This distinction matters for understanding financialization: as economies
shift from production to circulation (more sales, marketing, finance,
fewer factory workers), the share of unproductive labor grows. This
does not directly cause the rate of profit to fall (that's TRPF), but
it does mean that more of the surplus produced is consumed by circulation
rather than accumulated.

Integration with the Tick Pipeline
----------------------------------

The circulation module integrates into the annual economics pipeline
as a new step between imperial rent computation (step 4) and crisis
triggers (step 5). Each tick, the system:

1. Reads ``ValueTensor4x3`` from the ``TensorRegistry`` for department data
2. Reads ``CapitalStockCalculator.get_K()`` for capital stock
3. Computes ``CircuitState``, ``InventoryState``, ``DepreciationFundState``
4. Runs reproduction schema checks and crisis assessment
5. Writes results to ``CountyEconomicState.circulation_state``

The graph bridge serializes 7 ``tick_``-prefixed attributes to territory
nodes, making circulation data available to the UI, narrative system,
and endgame detector.

The ``CirculationCrisisState`` field sits alongside the existing
``CrisisState`` (TRPF) and ``BifurcationRiskMetric`` on
``CountyEconomicState``. The two crisis systems are parallel and
independent -- they model different theoretical mechanisms and their
signals can be consumed separately or combined by downstream systems.

See Also
--------

- :doc:`/reference/circulation-system` -- API reference for all types and functions
- :doc:`/concepts/volume-i-theory` -- Volume I: production of surplus value
- :doc:`/concepts/imperial-rent` -- Imperial rent and unequal exchange
- :doc:`/concepts/reproductive-labor` -- Department III and shadow labor
