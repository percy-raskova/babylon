The Marxian Value Tensor: Labor-Hours, Not Dollars
====================================================

The ValueTensor4x3 is Babylon's foundational economic data structure.
It encodes Marx's reproduction schema as a computable primitive,
measured in labor-hours rather than monetary units. This document
explains the theoretical reasoning behind the tensor's structure,
why labor-hours matter, and how the four departments map onto the
real economy.

.. contents:: On this page
   :local:
   :depth: 2

Why a Tensor?
-------------

Most economic simulations model GDP, wages, and prices — monetary
quantities that obscure the social relations they represent. A wage
of $30/hour tells you what the market pays, but not what the worker
*produces*. The difference between what a worker produces and what
they are paid is **surplus value** — the fundamental quantity of
capitalist exploitation. Monetary values hide this difference by
expressing both wages and output in the same unit (dollars),
making exploitation appear as mere "profit margin."

Marx's innovation in *Capital* was to measure everything in
**labor-hours** — the time socially necessary to produce
commodities. This makes exploitation directly visible: if a worker
works 8 hours but is paid wages equivalent to 4 hours of
labor-time, the remaining 4 hours are surplus value appropriated
by capital.

The ValueTensor4x3 implements this insight as a computational
primitive. Each cell contains labor-hours, not dollars. The
conversion from monetary values (QCEW wage data) to labor-hours
uses the Socially Necessary Labor Time (SNLT) conversion factor —
the monetary expression of labor time (MELT) inverted.

The Three Value Components
--------------------------

Every commodity contains three components of value, corresponding
to three types of labor:

Constant Capital (c)
~~~~~~~~~~~~~~~~~~~~

**Dead labor** — the labor-time embodied in the means of production
consumed during production: raw materials, depreciation of
machinery, energy, intermediate inputs. This value is *transferred*
to the product but not *created* anew; it merely reappears.

In BEA national accounts, constant capital corresponds to
**intermediate inputs** — the value of goods and services consumed
as inputs to production. The c/v ratio (organic composition of
capital) captures how capital-intensive an industry is: high c/v
means more machinery relative to workers, low c/v means more
labor-intensive.

Variable Capital (v)
~~~~~~~~~~~~~~~~~~~~

**Living labor paid** — the labor-time equivalent of wages. This
is "variable" because it is the only component that can expand
value: a worker paid for 4 hours' labor-time produces more than
4 hours of value. The difference is surplus value.

In QCEW data, variable capital corresponds to **total wages and
salaries**. The tensor converts these monetary wages to labor-hours
using the SNLT factor: ``v_hours = wages × snlt_factor``.

Surplus Value (s)
~~~~~~~~~~~~~~~~~

**Living labor unpaid** — the labor-time the worker performs but
is not compensated for. This is the source of profit, rent,
interest, and all forms of capitalist income. The exploitation
rate *e = s/v* measures the ratio of unpaid to paid labor.

BEA national accounts provide the basis for computing s/v ratios:
``s = gross_output − intermediate_inputs − compensation``. This
is value added minus labor costs — the surplus appropriated by
capital.

The Four Departments
--------------------

Marx's reproduction schema in *Capital Volume II* divides the
economy into departments based on the *use-value* of output — what
the products are *for*, not what industry produces them.

Department I: Means of Production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Capital goods that enter the production process as inputs:
machinery, raw materials, factory buildings, transportation
infrastructure, energy. Output from Department I replaces the
constant capital consumed across all departments.

**NAICS mapping**: Mining (21), Utilities (22), Construction (23),
heavy Manufacturing (31-33 partial), Wholesale Trade (42 partial).

**Economic significance**: Department I determines the rate of
accumulation. When Department I grows faster than Department II,
capital is investing in its own expansion — the accumulation
dynamic that drives the reserve army.

Department IIa: Necessary Consumption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wage goods consumed by workers: food, basic housing, clothing,
healthcare, transportation to work. Output from Department IIa
reproduces the labor force — it is what workers buy with their
wages.

**NAICS mapping**: Food manufacturing and retail (31, 44-45
partial), Healthcare (62), basic Transportation (48-49 partial),
basic Accommodation (72 partial).

**Economic significance**: Department IIa determines the
subsistence level. When productivity in IIa rises, the value of
labor power falls (workers can be reproduced with less
labor-time), which increases relative surplus value even without
changing wages.

Department IIb: Luxury Consumption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goods consumed by the bourgeoisie and labor aristocracy: luxury
housing, fine dining, art, yachts, financial services. Output from
Department IIb is purchased with surplus value — it does not
reproduce labor power.

**NAICS mapping**: Finance/Insurance (52), Real Estate (53),
luxury Retail (44-45 partial), Professional Services (54),
Arts/Entertainment (71).

**Economic significance**: Department IIb is where surplus value
is *realized* as consumption. The ratio of IIb to IIa output
reflects the class distribution of consumption — large IIb
relative to IIa indicates high inequality.

Department III: Social Reproduction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Care work and domestic labor: childcare, cooking, cleaning,
eldercare, emotional support, community maintenance. This is the
labor that reproduces the working class *outside* the wage
relation — what Fortunati calls the "hidden foundation" of
capitalist production.

**NAICS mapping**: Limited formal NAICS representation.
Approximated from ATUS (American Time Use Survey) data for unpaid
household labor, plus Healthcare (62 partial), Social Assistance
(62 partial), Education (61 partial).

**Economic significance**: Department III is the site of what
Babylon calls **shadow subsidy** — the value of reproductive labor
that is not monetized (not paid as wages) but is appropriated by
capital as a free input to labor-power reproduction. The
visibility scalar *g₃₃* controls what fraction of this labor the
price system recognizes.

The Visibility Scalar: g₃₃
---------------------------

Leopoldina Fortunati's *The Arcane of Reproduction* (1995) argues
that capitalist accumulation depends on the systematic
invisibility of reproductive labor. The price system treats care
work as a "natural" attribute of women and communities rather than
as productive labor that creates value.

The tensor encodes this through the visibility scalar *g₃₃*:

- **g₃₃ = 1.0**: All care work is monetized. Wages are paid for
  childcare, cooking, cleaning. The full cost of labor-power
  reproduction is visible to the price system. No shadow subsidy.

- **g₃₃ = 0.0**: All care work is invisible. Domestic labor is
  entirely unpaid. Capital appropriates the full value of
  reproductive labor as a free subsidy. Maximum shadow extraction.

- **g₃₃ = 0.3** (typical US estimate): About 30% of care work
  is formally monetized (daycare, restaurants, cleaning services).
  The remaining 70% is unpaid household labor — a shadow subsidy
  to capital that does not appear in GDP or wage statistics.

The **Fortunati exploitation rate** includes this shadow subsidy:

.. math::

   e_F = \frac{s + \text{shadow\_subsidy}}{v_{\text{monetized}}}

This is always higher than the standard exploitation rate
(*e = s/v*) because it counts the unpaid reproductive labor that
makes paid labor possible. The difference between *e_F* and *e*
is the measure of patriarchal extraction — the surplus
appropriated through the gendered division of labor.

SNLT and the Transformation Problem
------------------------------------

The Socially Necessary Labor Time (SNLT) conversion factor
transforms monetary values (prices) into labor-hours (values).
This is the inverse of the **Monetary Expression of Labor Time**
(MELT):

.. math::

   \text{SNLT factor} = \frac{1}{\text{MELT}}
   = \frac{\text{total labor-hours}}{\text{total value added}}

Until SNLT calibration is complete, the tensor uses a default
factor of 1.0, meaning values are **wage-proportional labor-time
proxies**. This has an important implication:

- **Ratios are exact**: exploitation rate (s/v), organic
  composition (c/v), and profit rate (s/(c+v)) are all
  unit-independent — the SNLT factor cancels in the numerator
  and denominator. These metrics are fully usable without
  calibration.

- **Magnitudes are approximate**: the absolute number of
  labor-hours in a tensor cell is only meaningful after SNLT
  calibration. Until then, the values represent wage-proportional
  proxies — they preserve relative ordering and derivatives but
  not absolute scale.

This separation of concerns means the simulation can operate
correctly on ratios and trends (which is what the contradiction
field system, Volume I mechanisms, and consciousness dynamics
need) while deferring the full transformation problem
(prices → values → prices of production) to a future
specification.

The NAICS-to-Department Mapping
--------------------------------

The mapping from NAICS industry codes to Marxian departments is
a theoretical act, not a technical one. The same industry can
produce commodities for multiple departments: a food manufacturer
produces both wage goods (IIa — basic groceries) and luxury goods
(IIb — artisanal cheese). The department mapping encodes an
analysis of the *social destination* of each industry's output.

The mapping uses allocation weights that sum to 1.0 per NAICS
code. Agriculture (NAICS 11) is allocated 62% to Department I
(raw materials as means of production), 33% to Department IIa
(food as wage goods), and 5% to Department IIb (luxury
agricultural products). These weights are configured in YAML,
not hardcoded, enabling recalibration as the analysis deepens.

**Excluded sectors**: Government (NAICS 92) is excluded from the
tensor entirely. Government does not operate within the M-C-M'
circuit — it does not produce commodities for exchange. Government
wages appear in the tensor as ``excluded_wages``, tracked but not
allocated to any department. This is a theoretical claim:
government workers produce use-values (roads, defense, education)
but not exchange-values within the capitalist circuit. Whether
this exclusion is correct is debatable; the simulation makes it
configurable.

The BEA Ratio Pipeline
-----------------------

The Bureau of Economic Analysis provides national-level
input-output data that yields the c/v and s/v ratios needed to
decompose wages into the three value components:

.. math::

   \frac{s}{v} = \frac{\text{gross output}
   - \text{intermediate inputs}
   - \text{compensation}}{\text{compensation}}

.. math::

   \frac{c}{v} = \frac{\text{intermediate inputs}}
   {\text{compensation}}

These ratios are industry-specific (NAICS-level) and
time-varying. The hydration pipeline uses a three-tier lookup
hierarchy:

1. **BEA empirical data** — most specific, interpolated across
   years within ±5 years
2. **Sector YAML** — 2-digit NAICS defaults from configuration
3. **Department defaults** — hardcoded fallback per department
   (e.g., Department I default c/v = 2.0 reflecting high capital
   intensity of means-of-production industries)

This hierarchy ensures the tensor always produces values (never
fails silently) while preferring empirical data when available.

Detroit Through the Tensor
--------------------------

The tensor reveals the economic structure of the Detroit
metropolitan area in labor-time terms:

**Wayne County** (26163): High variable capital (large workforce),
moderate-to-high exploitation rate (manufacturing wages below
value produced), positive imperial rent declining over time
(eroding labor aristocracy status). Department I dominant
(automotive manufacturing = means of production) with growing
Department IIa/III (service economy transition).

**Oakland County** (26125): High variable capital (professional
workforce), lower exploitation rate (higher wages relative to
value produced), strong positive imperial rent (suburban labor
aristocracy intact). Department IIb dominant (finance, real
estate, professional services = luxury consumption).

The exploitation gradient from Wayne to Oakland — visible in
the tensor's per-county exploitation rates — captures the
fundamental class geography of the Detroit metro area. The
tensor makes this *computable* rather than merely *observable*:
downstream systems (contradiction fields, reserve army, working
day classification) read from the tensor to drive their causal
mechanisms.

See Also
--------

- :doc:`/reference/tensor-primitive` — Data types, formulas,
  parameters, API reference
- :doc:`/concepts/imperial-rent` — Imperial rent theory
- :doc:`/concepts/reproductive-labor` — Reproductive labor and
  Department III
- :doc:`/concepts/volume-i-theory` — How Volume I mechanisms
  modify tensor values
