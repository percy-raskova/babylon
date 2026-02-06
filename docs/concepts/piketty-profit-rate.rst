Piketty's Rate of Return and Crisis Detection
==============================================

Why does the simulation use 5% as the crisis threshold? This document
explains how Piketty's rate of return framework, validated against the
World Inequality Database, produces an empirically grounded crisis
detection parameter.

.. contents:: On this page
   :local:
   :depth: 2

The Theoretical Framework
-------------------------

Thomas Piketty's central inequality is :math:`r > g`: when the rate of
return on capital (*r*) exceeds the economic growth rate (*g*), wealth
concentrates. When *r* falls toward *g*, the accumulation engine stalls
and crisis dynamics emerge.

Piketty quantifies the long-run parameters from centuries of data:

- **Historical r**: 4--5% per annum since antiquity (supported by
  land price-to-rent ratios of 20--25x in ancient Rome and
  pre-industrial Britain)
- **Long-run g**: ~1.5% per annum for developed countries at the
  technological frontier
- **Historical r - g gap**: 3.5--4.5% annually, representing the
  baseline wealth concentration dynamic

The twentieth century was the exception: world wars, inflation, and
capital regulation temporarily drove the gap negative. Piketty argues
the historical pattern is reasserting itself, with a projected future
gap of ~3% as *r* returns to its 4.5% long-run value.

The critical insight for crisis modeling: crisis does not require *r* to
reach zero. It emerges at the boundary where *r* approaches *g*,
preventing capital accumulation from driving secular inequality growth.
The system destabilizes not from absolute deprivation but from the
stalling of the accumulation engine that sustains class hierarchy.

Computing r from WID Data
-------------------------

Piketty's rate of return can be computed from two observable quantities
in the `World Inequality Database <https://wid.world/>`_ (WID):

.. math::

   r = \frac{\alpha}{\beta}

Where:

- :math:`\alpha` = capital share of national income (WID variable
  ``wcsnnii999``)
- :math:`\beta` = national wealth-to-income ratio (WID variable
  ``wnweali999``)

This decomposition is exact under national accounting identities:
if capital earns share :math:`\alpha` of national income and the total
capital stock is :math:`\beta` times national income, then the average
return on each unit of capital is :math:`\alpha / \beta`.

Capital Share: The Numerator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

US capital share of net national income (``wcsnnii999``), 1970--2024:

.. list-table::
   :header-rows: 1
   :widths: 15 15 50

   * - Period
     - Range
     - Pattern
   * - 1970--1985
     - 22--25%
     - Postwar baseline; labor's share at historical peak
   * - 1985--2000
     - 24--27%
     - Neoliberal shift; rising capital concentration
   * - 2000--2007
     - 26--28%
     - Pre-crisis peak; capital share surging
   * - 2008
     - 26.4%
     - Crisis compression: 90 bps below 2007 (27.3%)
   * - 2009--2015
     - 27--29%
     - Post-crisis surge exceeding pre-crisis levels
   * - 2020--2024
     - 28--30%
     - Record highs; 29.6% peak (2021--2022)

The crisis signature is visible but modest: capital share dipped from
27.3% to 26.4% during the 2008 financial crisis, then recovered within
two years and surged past pre-crisis levels. Capital share alone is too
stable to serve as a crisis indicator.

Wealth-to-Income Ratio: The Denominator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

US national wealth-to-income ratio (``wnweali999``), 1970--2024:

.. list-table::
   :header-rows: 1
   :widths: 15 15 50

   * - Period
     - Range
     - Pattern
   * - 1970--1985
     - 3.4--3.9x
     - Low baseline; capital stock modest relative to income
   * - 1985--2000
     - 3.9--4.7x
     - Asset price inflation begins; financialization
   * - 2000--2007
     - 4.7--5.3x
     - Housing bubble inflates wealth-to-income ratio
   * - 2008--2009
     - 4.8--4.3x
     - Crisis crash: 12.6% decline peak-to-trough
   * - 2010--2019
     - 4.1--5.6x
     - Gradual recovery then acceleration
   * - 2020--2024
     - 5.8--6.2x
     - Pandemic-era asset price inflation; record highs

The wealth-to-income ratio is far more volatile than capital share during
crises. The 2008 crash destroyed 12.6% of the ratio in two years
(5.34 to 4.31), while capital share fell only 3.3% (27.3% to 26.4%).
This asymmetry produces a counterintuitive result in the computed
profit rate.

The Computed Profit Rate
^^^^^^^^^^^^^^^^^^^^^^^^

Dividing capital share by wealth-to-income ratio yields the Piketty
profit rate for the US, 1970--2024:

.. list-table::
   :header-rows: 1
   :widths: 10 10 10 50

   * - Year
     - :math:`\alpha`
     - :math:`\beta`
     - :math:`r = \alpha / \beta`
   * - 1970
     - 23.3%
     - 3.43
     - **6.79%**
   * - 1975
     - 23.6%
     - 3.44
     - **6.86%**
   * - 1980
     - 23.1%
     - 4.28
     - **5.40%**
   * - 1982
     - 23.9%
     - 3.87
     - **6.18%**
   * - 1990
     - 25.7%
     - 4.03
     - **6.38%**
   * - 2001
     - 24.5%
     - 4.81
     - **5.09%**
   * - 2007
     - 27.3%
     - 5.34
     - **5.11%**
   * - 2008
     - 26.4%
     - 4.77
     - **5.53%**
   * - 2009
     - 27.1%
     - 4.31
     - **6.28%**
   * - 2012
     - 29.8%
     - 4.09
     - **7.31%** (historical max)
   * - 2019
     - 28.5%
     - 5.62
     - **5.07%**
   * - 2020
     - 28.7%
     - 6.16
     - **4.66%** (historical min)
   * - 2024
     - 27.8%
     - 5.85
     - **4.75%**

**Summary statistics** (1970--2024):

- Mean: 6.07%
- Std: 0.70%
- Min: 4.66% (2020, pandemic)
- Max: 7.31% (2012)
- P10: 5.09%
- P25: 5.45%
- Median: 6.15%

A Counterintuitive Finding
^^^^^^^^^^^^^^^^^^^^^^^^^^

During the 2008 financial crisis, the computed *r* actually **rose** from
5.11% (2007) to 5.53% (2008) to 6.28% (2009). This is not a data error.
The wealth-to-income ratio (the denominator) crashed faster than capital
share (the numerator): asset valuations collapsed while the flow of
profits compressed more slowly. The same unit of remaining capital earned
a higher *return* precisely because so much capital stock had been
destroyed.

This reveals what the Piketty profit rate actually measures: not the
health of the economy, but the *scarcity premium on surviving capital*.
Crisis destroys wealth faster than it destroys income flows, temporarily
inflating returns on whatever capital remains.

The crisis signal in *r* therefore appears **before** the crash (2007:
5.11%) rather than during it. The pre-crisis compression reflects the
bubble dynamics: inflated asset valuations (high :math:`\beta`) suppress
returns (low *r*) even as profits (:math:`\alpha`) appear robust. When
*r* falls below 5%, the economy has entered a zone where capital is
overvalued relative to its income-generating capacity---the precondition
for a correction.

Crisis Threshold Derivation
---------------------------

The 5% Boundary
^^^^^^^^^^^^^^^^

Every significant US recession since 2000 occurred when the Piketty
profit rate *r* fell to or below 5.1%:

.. list-table::
   :header-rows: 1
   :widths: 20 15 45

   * - Crisis
     - Piketty *r*
     - Context
   * - Dot-com (2001)
     - 5.09%
     - Overvalued tech assets; :math:`\beta` surged
   * - Financial crisis (2007)
     - 5.11%
     - Housing bubble; :math:`\beta` at 5.34x
   * - Pre-pandemic (2019)
     - 5.07%
     - Extended asset inflation; :math:`\beta` at 5.62x
   * - Pandemic (2020)
     - 4.66%
     - Extreme shock; :math:`\beta` spiked to 6.16x

The P10 of the full 1970--2024 distribution sits at 5.09%, confirming
that *r* below 5% represents the bottom decile of historical experience.

Earlier crises (1973--75, 1980--82, 1990--91) show higher *r* values
(5.4--6.8%) because wealth-to-income ratios were structurally lower in
that era. The 5% threshold is a modern-era phenomenon that reflects the
secular rise in :math:`\beta` documented by Piketty---as wealth-to-income
ratios have doubled since the 1970s, the crisis boundary for *r* has
compressed downward.

Sensitivity Tiers
^^^^^^^^^^^^^^^^^

The empirical data supports a three-tier threshold structure:

.. list-table::
   :header-rows: 1
   :widths: 15 15 50

   * - Threshold
     - Label
     - Empirical basis
   * - 6%
     - Conservative
     - Below long-run mean (6.07%); marks transition from
       expansion to compression
   * - **5%**
     - **Moderate**
     - **P10 boundary; all post-2000 recessions at or below
       this level (recommended default)**
   * - 4%
     - Severe
     - Below all historical observations except 2020 pandemic
       (4.66%); approaching Piketty's theoretical floor

The simulation uses 5% as the default ``r_threshold`` in
:ref:`Feature 018 <spec-018>`, with the understanding that this
parameter is configurable for scenario exploration.

Relationship to Marxist Profit Rate
------------------------------------

The Piketty profit rate (:math:`r = \alpha / \beta`) and the Marxist
rate of profit (:math:`r' = s / (c + v)`) measure related but distinct
quantities:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Dimension
     - Piketty *r*
     - Marxist *r'*
   * - Numerator
     - Capital share of national income
     - Surplus value (*s*)
   * - Denominator
     - Total capital stock (wealth-to-income ratio)
     - Constant + variable capital (*c* + *v*)
   * - Scope
     - All capital income (rent, profit, interest)
     - Industrial profit only
   * - Historical range
     - 4.66--7.31% (US 1970--2024)
     - 12--22.7% (US 1947--2003)
   * - Crisis floor
     - ~5% (modern era)
     - ~13% (postwar era)

The Marxist rate is systematically higher because its denominator
(*c* + *v*, the capital advanced for production) is smaller than
Piketty's denominator (total national wealth including land, housing,
financial assets). The Piketty rate captures the return on *all* wealth,
while the Marxist rate captures the return on *productive* capital only.

For crisis detection, the simulation uses Piketty's formulation because:

1. It is computable from the simulation's existing economic state
   (capital share and wealth-to-income ratio are derived quantities)
2. It captures the financialization dynamics that characterize modern
   crises (asset bubbles inflate :math:`\beta`, suppressing *r*)
3. It aligns with the empirical WID dataset, enabling validation
   against 50+ years of observed data

The Marxist profit rate remains central to the simulation's
:doc:`imperial-rent` calculations and the
:py:func:`~babylon.formulas.trpf.calculate_rate_of_profit` formula.
The two rates are complementary: Piketty's *r* detects macro-level
crisis onset, while the Marxist *r'* drives micro-level class dynamics.

Dimensional Analysis: Hours, Dollars, and the MELT Bridge
---------------------------------------------------------

Babylon's fundamental tensor operates in **labor-hours** (socially
necessary labor time), not nominal dollars. The MELT
(:math:`\tau = \text{GDP} / L`, where *L* is total labor-hours) bridges
between the labor-time domain and the money-price domain. Piketty's WID
data is denominated in nominal dollars. Does this unit mismatch
invalidate the threshold?

Why Units Cancel in Ratios
^^^^^^^^^^^^^^^^^^^^^^^^^^

Profit rates are dimensionless ratios. The MELT cancels:

.. math::

   r' = \frac{s}{c + v} = \frac{\tau \cdot s}{\tau \cdot c + \tau \cdot v}
      = \frac{s_\$ }{c_\$  + v_\$ }

Whether computed in labor-hours or dollars, the numerical value is
identical. The 5% threshold derived from dollar-denominated WID data
applies equally to an hours-denominated tensor --- **provided all
components of the formula use the same unit system**.

This is confirmed empirically: the
:class:`~babylon.economics.tensor.ValueTensor4x3` computes
``profit_rate = total_s / (total_c + total_v)`` entirely in labor-hours,
and validates against Piketty's 3--8% bounds in integration tests
(``PIKETTY_R_MIN = 0.03``, ``PIKETTY_R_MAX = 0.08``).

Two Profit Rates in the Codebase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simulation computes profit rate in two places using different
formulas and different denominators:

.. list-table::
   :header-rows: 1
   :widths: 15 25 20 20

   * - Rate
     - Formula
     - Units
     - Location
   * - **Flow-based**
     - :math:`r' = s / (c + v)`
     - All labor-hours
     - :class:`~babylon.economics.tensor.ValueTensor4x3`
       (``tensor.py:349``)
   * - **Stock-based**
     - :math:`r = s / (K + v)`
     - Mixed (see below)
     - :class:`~babylon.economics.tick.derived_rates.DerivedRateCalculator`
       (``derived_rates.py:71``)

The **flow-based** rate uses constant capital *consumed in one period*
(:math:`c`). It is dimensionally consistent: :math:`c`, :math:`v`, and
:math:`s` all come from ValueTensor4x3 in labor-hours.

The **stock-based** rate uses *accumulated* capital stock (:math:`K`)
from the perpetual inventory method:
:math:`K[t+1] = K[t] \times (1 - \delta) + c[t]`, where
:math:`\delta = 0.07`. At steady state, :math:`K \approx c / \delta
\approx 14.3 \times c`, making the stock-based denominator much larger
and the rate much lower than the flow-based rate.

The stock-based rate is what Feature 018's crisis detector consumes
(FR-001, A-001). This is theoretically correct: *K* represents the full
capital stock against which returns are measured, matching Piketty's
:math:`\beta` in spirit (total wealth, not just one period's investment).

.. _dimensional-mismatch:

Dimensional Mismatch in the Tick Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   The ``DerivedRateCalculator`` currently mixes unit systems in its
   stock-based profit rate computation. This must be reconciled before
   Feature 018 can use the rate for crisis detection.

The data flow in ``DerivedRateCalculator.compute_county_rates()``
(``derived_rates.py:42--94``):

.. code-block:: text

   v = v_reproduction × annual_hours        # ($/hour) × hours = DOLLARS
   total_value = tau × annual_hours          # ($/hour) × hours = DOLLARS
   s = total_value - v                       # dollars - dollars = DOLLARS

   K = county.capital_stock                  # From CapitalStockCalculator
                                             # = total_c / δ = LABOR-HOURS

   profit_rate = s / (K + v)                 # DOLLARS / (LABOR-HOURS + DOLLARS)
                                             #   ← dimensional inconsistency

The ``capital_stock`` field in ``CountyEconomicState`` is seeded from
:meth:`~babylon.economics.capital_stock.CapitalStockCalculator.get_K`,
which computes *K* via the perpetual inventory method on ``total_c`` from
ValueTensor4x3 --- all in **labor-hours**. But ``s`` and ``v`` are
computed as ``tau × hours`` and ``v_reproduction × hours`` ---
both in **dollars**.

Adding labor-hours to dollars in the denominator produces a
dimensionally incoherent quantity.

Why It Has Not Been Caught
""""""""""""""""""""""""""

The Piketty guardrail tests (``PIKETTY_R_MIN = 0.03``,
``PIKETTY_R_MAX = 0.08``) validate ``ValueTensor4x3.profit_rate`` ---
the **flow-based** rate, which is dimensionally consistent. The
**stock-based** rate in ``DerivedRateCalculator`` has not been validated
end-to-end against empirical bounds because the tick dynamics pipeline
(Feature 017) was recently implemented and the full pipeline has not
yet run with real hydrated data feeding both the tensor and the capital
stock calculator simultaneously.

Resolution Options
""""""""""""""""""

Three approaches to reconcile the units:

1. **Convert K to dollars before use**: Multiply ``capital_stock`` by
   :math:`\tau` when computing the stock-based rate. This keeps the
   ``DerivedRateCalculator`` in the dollar domain:
   :math:`r = s_\$ / (\tau \cdot K_h + v_\$ )`.

2. **Compute s and v in labor-hours**: Divide ``s`` and ``v`` by
   :math:`\tau` (or equivalently, source them from the tensor directly
   rather than recomputing from ``tau × hours``). This keeps everything
   in the hours domain:
   :math:`r = s_h / (K_h + v_h)`.

3. **Use the flow-based rate for crisis detection**: Bypass the
   stock-based rate entirely. The flow-based rate from
   ValueTensor4x3 is already dimensionally consistent and validates
   against Piketty bounds. The tradeoff: flow-based uses :math:`c`
   (one period's capital consumption) rather than :math:`K` (accumulated
   stock), which is less theoretically aligned with Piketty's
   :math:`\beta` but numerically validated.

Option 2 is the cleanest because it preserves the labor-time
foundation of the tensor system (the simulation's single source of
truth) while using the theoretically correct stock-based denominator.
Option 1 introduces a dollar-denominated pathway that diverges from the
tensor's hours-first architecture. Option 3 sacrifices theoretical
precision for expedience.

.. note::

   Regardless of which option is chosen, the **numerical value** of
   the profit rate will be the same (MELT cancels in ratios). The
   issue is not that the current code produces wrong numbers at
   runtime --- it is that the formula as written is dimensionally
   malformed, which means the code is *accidentally correct* only
   if :math:`\tau \approx 1.0`. At the actual US MELT of ~$62/hour,
   the current formula would produce a meaningless value.

Implications for r_threshold
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the dimensional mismatch is resolved, the r_threshold of 5%
applies to the stock-based rate. The key question is whether the
stock-based rate lands in the same numerical range as the Piketty rate:

- **Flow-based** :math:`s/(c+v)`: Validated at 3--8% from real data
  (Piketty guardrails pass).
- **Stock-based** :math:`s/(K+v)` where :math:`K \approx 14.3 \times c`:
  The denominator is ~14x larger for the *K* component, so the rate
  will be substantially lower than the flow-based rate.

If the flow-based rate is ~5% and :math:`K \approx 14.3c`, then with
typical OCC values (:math:`c \approx 2v`):

.. math::

   r_{\text{stock}} = \frac{s}{K + v} = \frac{s}{14.3c + v}
   \approx \frac{0.05 \times (c + v)}{14.3c + v}
   = \frac{0.05 \times 3v}{28.6v + v} \approx 0.5\%

This suggests the stock-based rate may be an order of magnitude lower
than the flow-based rate, placing it well below the 5% Piketty threshold
permanently. The r_threshold would need to be recalibrated for the
stock-based formula, or the crisis detector should consume the
flow-based rate instead.

This calibration question is deferred to Feature 018 implementation
planning, where empirical validation against hydrated county data will
determine the correct rate formula and threshold pairing.

Corroborating Sources
---------------------

The 5% threshold was cross-validated against multiple independent
analyses:

**Fred Moseley** (1947--1977): Documented US profit rate decline from
22% to 12%, establishing the postwar compression trajectory. The 12%
nadir (1977) in Marxist terms corresponds to a Piketty *r* of
approximately 5.5--6.5% given 1970s wealth-to-income ratios of 3.4--3.9x.

**Michael Roberts** (1946--2020): Calculated 27% secular decline in US
profitability since 1946 using Marxist methodology. Roberts projects
a 3% crisis floor for the non-financial corporate sector, which aligns
with a Piketty *r* of approximately 4--5% under modern :math:`\beta`
values.

**BEA Corporate Profits** (1950--2024): Corporate profit-to-GDP ratio
ranged from 8% (2000s crisis) to 22% (post-2015 peak), with 16--17%
as the postwar baseline. The 8% crisis floor in GDP terms corresponds
to compressed *r* values in the 4.5--5.5% Piketty range.

**Macroeconomic calibration literature**: The standard calibration for
real return on private market capital across DSGE models is 4%, derived
from stock market returns (~7%) averaged with risk-free bonds (~0.8%).
This aligns with Piketty's historical estimate and the simulation's
crisis floor.

Data Source
-----------

All empirical values in this document are derived from the
`World Inequality Database <https://wid.world/>`_ (WID), using the
US country dataset (``WID_data_US.csv``).

**Variables used**:

- ``wcsnnii999``: Capital share of net national income (percentage,
  all population, national total). The share of national income
  accruing to capital owners rather than labor.
- ``wnweali999``: National wealth-to-income ratio (ratio, all
  population, national total). Total national wealth divided by
  national income, measuring how many years of income the capital
  stock represents.

**Methodology**: WID data follows the Distributional National Accounts
(DINA) methodology, combining national accounts, survey data, and tax
records to produce consistent distributional series. All values use
the ``999`` population qualifier (entire adult population) and ``i``
suffix (interpolated/estimated for complete time coverage).

The WID dataset used for this analysis was exported in February 2026 and
covers 1970--2024 for both variables.

See Also
--------

- :doc:`imperial-rent` -- How imperial rent connects to profit rate
  dynamics
- :doc:`terminal-crisis` -- The endgame when crisis mechanics resolve
- :doc:`theory` -- MLM-TW theoretical foundation
- :doc:`/reference/formulas` -- Formula reference including TRPF
- :class:`~babylon.economics.tensor.ValueTensor4x3` -- Flow-based
  profit rate (dimensionally consistent, Piketty-validated)
- :class:`~babylon.economics.tick.derived_rates.DerivedRateCalculator`
  -- Stock-based profit rate (dimensional reconciliation pending)
- :class:`~babylon.economics.capital_stock.CapitalStockCalculator`
  -- Capital stock K in labor-hours (perpetual inventory method)
