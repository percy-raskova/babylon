The Economics Pipeline: From Value to Class Struggle
=====================================================

Five features (012–016) form a computational pipeline that
transforms raw economic data into the dynamics of class struggle.
This document explains the theoretical chain: how capital
accumulates, how labor-time becomes visible or invisible, how
counties are positioned in the imperial division of labor, and
how all of this drives the formation and dissolution of class
positions.

.. contents:: On this page
   :local:
   :depth: 2

The Pipeline as Causal Chain
----------------------------

The economics pipeline implements a specific theoretical claim:
**class positions are determined by material conditions, and
material conditions are determined by the dynamics of capital
accumulation.** Each feature in the chain adds one link:

1. **Capital stock** (012): How past investment becomes present
   productive capacity
2. **MELT** (013): How to measure labor-time in a monetary
   economy
3. **Throughput** (014): Where each county sits in the imperial
   division of labor
4. **Visibility** (015): How much labor is invisible to the
   price system
5. **Class dynamics** (016): How all of the above drives class
   formation and dissolution

This is not an arbitrary ordering. Each feature depends on
the one before it, and the whole chain depends on the
ValueTensor4x3 (Feature 011) as its foundation. The pipeline
makes it possible to start from BLS wage data and arrive at
a simulated class distribution that can be compared against
Census wealth data.

Capital Stock and the Falling Rate of Profit
---------------------------------------------

Marx's most controversial claim in *Capital Volume III* is that
the rate of profit tends to fall over time as capital accumulates.
The mechanism is straightforward: as firms invest in machinery
(constant capital *c*), the organic composition of capital
(*c/v*) rises. Since only living labor (*v*) creates new value,
and surplus value (*s*) comes from living labor, the profit rate
*r = s/(c+v)* tends to decline as *c* grows relative to *v*.

Feature 012 makes this computable by tracking accumulated capital
stock *K* through the **perpetual inventory method**:

.. math::

   K_{t+1} = K_t \cdot (1 - \delta) + c_t

Each year, capital depreciates by rate δ (default 7%) and is
replenished by new investment (total constant capital consumed,
*c_t*, from the tensor). The **stock-based profit rate**
*r = s/(K+v)* captures the TRPF dynamic: as *K* accumulates
over time, the denominator grows while *s* (limited by living
labor) cannot keep pace.

The distinction between stock-based and flow-based profit rates
matters because the TSSI (Temporal Single-System Interpretation)
values capital at historical cost, not replacement cost.
Accumulated *K* reflects *what was actually invested*, including
investments made when technology was more expensive. This is why
the profit rate falls even when individual firms appear
profitable: the accumulated weight of past investment drags
down the average return.

The initial condition *K₀ = c₀/δ* assumes steady state — the
economy has been operating long enough for capital stock to
reach its equilibrium level. This is a simplifying assumption
that works well for the 2010+ period but would need adjustment
for modeling structural breaks.

The Monetary Expression of Labor Time
--------------------------------------

The MELT (τ) solves a fundamental measurement problem: how do
you measure labor-time in an economy that denominates everything
in dollars?

Marx's labor theory of value asserts that the value of a commodity
is determined by the socially necessary labor time required to
produce it. But wages, prices, and GDP are all reported in
monetary units. The MELT provides the conversion factor:

.. math::

   \tau = \frac{\text{GDP}}{\text{total labor-hours}}
   = \frac{\text{GDP}}{\text{employment} \times 2080}

τ tells you how many dollars one hour of labor-time is
*expressed as* in the current monetary system. For the US in
recent years, τ ≈ $60–70/hour — meaning each hour of socially
necessary labor time is expressed as roughly $65 in GDP.

This is not a wage. It is a structural property of the entire
economy. Individual wages can be above or below τ. A worker
earning $90/hour (above τ) is *commanding more labor-time than
they perform* — they are a net extractor, benefiting from
imperial rent. A worker earning $40/hour (below τ) is *donating
labor-time* — they are net exploited.

The Basket Visibility Problem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The MELT would be straightforward if all commodities were
produced domestically. But the US imports roughly 25% of its
consumption from countries where labor is systematically
undervalued — where the same physical commodity embodies more
labor-time but costs fewer dollars.

The **basket visibility** coefficient γ_basket corrects for this:

.. math::

   \gamma_{\text{basket}} = \frac{1}
   {\frac{\alpha}{\gamma_{\text{import}}} + (1 - \alpha)}

Where α is the import share of consumption and γ_import measures
how much labor-time is made invisible by the exchange rate
deviation. When γ_basket < 1, the consumption basket contains
more labor-time than its price suggests — the difference is
imperial rent extracted from the periphery.

The **effective MELT** (τ_eff = τ × γ_basket) is the threshold
that determines class position: a worker earning above τ_eff is
a net beneficiary of the imperial system; below τ_eff is a net
contributor.

Imperial Rent Per Hour
~~~~~~~~~~~~~~~~~~~~~~

The most politically significant metric in the pipeline:

.. math::

   \Phi_{\text{hour}} = \frac{W}{\tau \cdot \gamma_{\text{basket}}} - 1

Φ_hour > 0 means this worker commands more labor-time per hour
than they perform. Φ_hour < 0 means they donate labor-time to
capital. Φ_hour = 0 is break-even.

A critical theoretical distinction: **Φ_hour is a flow metric,
not a class position.** A proletarian worker (bottom 50% wealth)
can have Φ_hour > 0 if their wages are above τ_eff, while
remaining proletarian because their accumulated wealth is below
the threshold. Class position is determined by wealth stock, not
income flow. This separation prevents the common error of
equating high wages with bourgeois class position.

Throughput: The Geography of Value
-----------------------------------

Feature 014 answers the question: how much value does each
county produce per labor-hour, and how does that compare to
the national average?

The **throughput intensity** τ_through is the county-level
analogue of the national MELT. The **throughput position**
π = τ_through/τ_national tells you whether a county is above or
below the national average in value production per labor-hour.

This is not just a productivity metric. It captures the county's
position in the **imperial division of labor**:

- **π > 1** (Oakland County): More value produced per hour than
  national average. Finance, professional services, corporate
  headquarters — the command nodes of capital.

- **π < 1** (Wayne County): Less value per hour than average.
  Manufacturing, logistics, service work — the production nodes
  where surplus is extracted.

The **supply chain depth** metric (0–5 scale) adds a structural
dimension: extraction industries (depth 0) produce raw inputs,
manufacturing (depth 1.5) transforms them, and finance (depth
5.0) appropriates value without producing physical commodities.
Counties with high depth and high π are the command-and-control
centers of American capitalism. Counties with low depth and low
π are the sites of direct exploitation.

The **commuter-adjusted** variant uses LODES data to distinguish
between where people *work* and where they *live*. A county like
Wayne (net job exporter — more people commute in than out) has
higher workplace throughput than residence throughput. This
matters because value is produced at the workplace but consumed
at the residence, and the two may be in different counties with
different class compositions.

The Three Invisibilities
-------------------------

Feature 015 computes three visibility coefficients that measure
how much labor is hidden from the price system. Each represents
a distinct mechanism of exploitation:

Reproductive Labor Invisibility (γ_III)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Leopoldina Fortunati's insight: capitalism depends on unpaid
reproductive labor (childcare, cooking, cleaning, eldercare)
that reproduces the working class but is not recognized as
productive labor. The ratio of paid to total care work:

.. math::

   \gamma_{\text{III}} = \frac{L_{\text{paid}}}{L_{\text{paid}}
   + L_{\text{unpaid}}}

US estimate: γ_III ≈ 0.30 — only 30% of care work is monetized.
The remaining 70% is performed overwhelmingly by women, without
compensation, and appropriated by capital as a free subsidy to
the reproduction of labor power.

The **shadow subsidy** Φ_III quantifies this: the dollar value
of unpaid care work, computed as the labor-hours times the MELT.
This is what it would cost capital if all care work had to be
purchased at market rates — the hidden foundation of profitability
that feminist political economy reveals.

Import Invisibility (γ_import)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arghiri Emmanuel's **unequal exchange** thesis: when peripheral
countries trade with core countries, exchange rates systematically
undervalue peripheral labor. The Exchange Rate Deviation Index
(ERDI) measures this: ERDI = GDP_PPP / GDP_MER. India's ERDI of
2.80 means Indian labor is valued at roughly 1/2.8 of its true
labor-time equivalent in dollar terms.

When the US imports commodities from India, it receives 2.8 hours
of Indian labor-time for every 1 hour's worth of dollars it pays.
The γ_import coefficient captures this across all import partners:

.. math::

   \gamma_{\text{import}} = \sum_i
   \frac{s_i}{\text{ERDI}_i}

A low γ_import (more imports from high-ERDI periphery) means more
invisible labor in the consumption basket — more imperial rent
extracted from the global working class.

Composite Basket Invisibility (γ_basket)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The combined effect of import invisibility and domestic
consumption share:

.. math::

   \gamma_{\text{basket}} = \frac{1}
   {\frac{\alpha}{\gamma_{\text{import}}} + (1 - \alpha)}

This is the harmonic mean that weights import invisibility by
the import share. It is always ≥ γ_import (mathematically
guaranteed), capturing the fact that domestic production at
ERDI=1 dilutes the import invisibility.

Class Dynamics: The Engine of History
--------------------------------------

Feature 016 closes the pipeline by simulating how all the
upstream metrics drive the formation and dissolution of class
positions over time. The class distribution evolves through four
transition flows operating each tick:

The Four Flows
~~~~~~~~~~~~~~~

**Dispossession** (LA → Proletariat): Foreclosure, bankruptcy,
and eviction strip accumulated wealth from labor aristocracy
households, pushing them below the wealth threshold into
proletarian status. The rate is a weighted composite of
foreclosure (60%), bankruptcy (30%), and eviction (10%) rates —
reflecting that housing wealth loss (foreclosure) is the primary
mechanism of downward class mobility in the US.

**Accumulation** (Proletariat → LA): Workers save from wages
(including the imperial rent bonus Φ_hour, capped at 5% uplift)
and gradually accumulate wealth above the threshold. The savings
rate is class-differentiated (proletariat: 3%, LA: 12%), reflecting
the empirical finding from the Fed Survey of Consumer Finances
that savings rates rise sharply with wealth.

**Precaritization** (Proletariat → Lumpen): Unemployment and
eviction push proletarian workers into the lumpenproletariat —
the surplus population excluded from stable employment. This
rate combines unemployment and eviction rates, reflecting the
two primary pathways to permanent exclusion.

**Stabilization** (Lumpen → Proletariat): Some lumpenproletariat
workers are reabsorbed into stable employment, especially during
economic expansions. The rate is proportional to (1 - unemployment)
— when unemployment is low, more marginal workers find jobs.

Crisis Amplification
~~~~~~~~~~~~~~~~~~~~~

During economic crises, all flows accelerate: dispossession and
precaritization rates multiply (up to 3.5× in deep crisis) while
accumulation and stabilization rates collapse (down to 0.1× and
0.2×). This captures the empirical reality of crisis dynamics:
the 2008 crisis simultaneously accelerated foreclosures,
eliminated savings capacity, and froze hiring — pushing the class
distribution rapidly toward polarization.

The phased crisis model (NORMAL → ONSET → EARLY → DEEP →
RECOVERY) allows the simulation to capture the temporality of
crisis: the slow onset, the accelerating collapse, the depth of
trough, and the partial recovery — each phase with its own
characteristic amplification pattern.

Detroit Through the Pipeline
-----------------------------

The full pipeline produces a concrete analysis of the Detroit
metropolitan area:

1. **Tensor** (011): Wayne County has high total_c (manufacturing
   capital), moderate total_v (declining wages), and rising
   exploitation rate as wages fall faster than output.

2. **Capital stock** (012): Wayne's accumulated K is high but
   depreciating (factory closures). Oakland's K is growing
   (new commercial/financial investment). The stock-based profit
   rate falls in Wayne, rises in Oakland.

3. **MELT** (013): National τ ≈ $65/hour. Wayne workers earning
   $45K/year ($21.6/hr) have Φ_hour < 0 — they are net exploited.
   Oakland workers at $62K ($29.8/hr) may have Φ_hour > 0 — net
   extractors, depending on γ_basket.

4. **Throughput** (014): Wayne has π < 1 (below-average value per
   labor-hour, manufacturing/logistics). Oakland has π > 1
   (above-average, finance/professional services). The supply
   chain depth gradient captures the structural asymmetry.

5. **Visibility** (015): γ_III ≈ 0.30 nationally. The shadow
   subsidy falls disproportionately on Wayne County's larger
   working-class population, where unpaid care work substitutes
   for services that Oakland residents can afford to purchase.

6. **Class dynamics** (016): The 2008 crisis amplifies
   dispossession in Wayne (high foreclosure rates → LA → Prol
   flow), collapses accumulation (savings wiped out), and
   accelerates precaritization (unemployment spike). The class
   distribution polarizes: Wayne's labor aristocracy shrinks,
   proletariat and lumpenproletariat grow. Oakland, with lower
   dispossession rates and higher accumulation capacity, is
   relatively insulated — its class distribution shifts slowly.

This is the pipeline's theoretical payoff: a computable,
empirically grounded account of how the same crisis produces
different class dynamics in adjacent counties, determined not by
culture or politics but by the material structure of capital
accumulation and imperial rent.

See Also
--------

- :doc:`/reference/economics-pipeline` — Data types, formulas,
  and parameters
- :doc:`/concepts/tensor-theory` — ValueTensor4x3 foundations
- :doc:`/concepts/imperial-rent` — Imperial rent theory
- :doc:`/concepts/volume-i-theory` — Volume I production dynamics
- :doc:`/concepts/reproductive-labor` — Reproductive labor and
  Department III
- :doc:`/concepts/unified-class-system` — Community filtration,
  dual-criteria validation, and class-pair solidarity
