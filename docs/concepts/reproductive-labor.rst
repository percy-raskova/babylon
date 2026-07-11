.. _reproductive-labor:

===================
Reproductive Labor
===================

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
========

Reproductive labor refers to the work that maintains and reproduces labor power
itself: cooking, cleaning, childcare, elder care, emotional support, and all the
invisible labor that enables workers to return to work each day. In the Babylon
simulation, this is modeled through **Department III** of the 4-department
Marxian reproduction schema.

The key insight from proletarian feminist theory is that reproductive labor is
**necessary** for capital accumulation but **invisible** to economic measurement.
The visibility tensor (``g₃₃``) makes this labor visible by distinguishing between
monetized care work and unpaid domestic labor.

Theoretical Foundation
======================

Proletarian Feminist Sources
-----------------------------

The Babylon model draws on several key texts in proletarian feminist theory:

**Leopoldina Fortunati** - *The Arcane of Reproduction* (1981)
   Argues that domestic labor produces labor-power (the commodity workers sell).
   This labor is doubly invisible: unpaid AND unrecognized as productive. The
   housewife is exploited by capital through the mediation of the male wage.
   Reproductive labor is not "outside" capitalism but central to it.

**Silvia Federici** - *Caliban and the Witch* (2004)
   The witch hunts were primitive accumulation against women's bodies. Capitalism
   required the disciplining of women into unpaid reproductive labor. The wage
   is a tool of division - it hides the unwaged labor that makes waged labor
   possible.

**Claude Meillassoux** - *Maidens, Meal and Money* (1981)
   The "domestic community" is a mode of production that capitalism parasitizes.
   Capitalism extracts labor-power without paying for its full reproduction costs.
   The periphery (and domestic sphere) subsidizes the core. This is
   "superexploitation" - extraction below the value of labor-power.

**MIM Prisons** - *Gender and Revolutionary Feminism*
   Gender oppression intersects with national oppression. First World "workers"
   often receive more than the value they produce (negative exploitation in core).
   The Fortunati rate going to infinity in the periphery is the mathematical
   inverse of the labor aristocracy receiving more than they produce in the core.

Core Insight: Shadow Labor as Appropriated Surplus
--------------------------------------------------

The central theoretical insight is that **shadow labor is not merely unpaid
costs** - it is **appropriated surplus value**. The capitalist class benefits
twice:

1. They pay less V (variable capital/wages)
2. They capture the surplus labor time of the reproductive sphere

This is analogous to imperial rent in the core-periphery relation:

.. list-table:: Parallel Structures of Extraction
   :header-rows: 1
   :widths: 30 35 35

   * - Concept
     - Definition
     - Mechanism
   * - **Imperial Rent**
     - Value transfer from periphery to core
     - Unequal exchange in global commodity circuit
   * - **Shadow Labor**
     - Value transfer from household to capital
     - Unpaid labor excluded from wage

The Visibility Tensor
=====================

Mathematical Definition
-----------------------

The visibility scalar ``g₃₃`` determines what fraction of Department III labor
is visible to the price system:

.. math::

   g_{33} \in [0.0, 1.0]

Where:

- ``g₃₃ = 1.0``: All Dept III labor is monetized (standard Marxian analysis)
- ``g₃₃ = 0.0``: All Dept III labor is unpaid (extreme invisibility)
- ``g₃₃ = 0.3``: ATUS 2022 national estimate (~30% monetized, 70% shadow)
- ``g₃₃ = 0.5``: Half visible, half shadow (typical household)

Computed Properties
-------------------

The visibility tensor enables several computed properties on ``ValueTensor4x3``:

**monetized_value**
   Total value visible to the price system:

   .. math::

      V_{monetized} = \sum_{i \in \{I, IIa, IIb\}} V_i + V_{III} \times g_{33}

**monetized_v**
   Wages actually paid:

   .. math::

      v_{monetized} = v_I + v_{IIa} + v_{IIb} + (v_{III} \times g_{33})

**shadow_subsidy**
   Unpaid reproductive labor appropriated as surplus:

   .. math::

      \text{shadow} = v_{III} \times (1 - g_{33})

**exploitation_rate_fortunati**
   The expanded exploitation rate recognizing shadow labor:

   .. math::

      e' = \frac{s_{total} + \text{shadow\_subsidy}}{v_{monetized}}

Canonical Example: The 300% Rate
--------------------------------

Consider a simplified economy with only Department III:

- ``v = 100`` (variable capital)
- ``s = 100`` (surplus value)
- ``g₃₃ = 0.5`` (half monetized)

**Standard exploitation rate:**

.. math::

   e = \frac{s}{v} = \frac{100}{100} = 100\%

**Fortunati exploitation rate:**

.. math::

   \text{monetized\_v} &= 100 \times 0.5 = 50 \\
   \text{shadow\_subsidy} &= 100 \times (1 - 0.5) = 50 \\
   e' &= \frac{100 + 50}{50} = \frac{150}{50} = 300\%

The shadow labor **triples** the apparent exploitation rate. This dramatic
increase reflects Fortunati's insight that recognizing shadow labor as
appropriated surplus fundamentally changes how we measure exploitation.

The Infinity Dialectic
======================

When Does Infinity Occur?
-------------------------

The Fortunati exploitation rate becomes infinite when ``monetized_v = 0``:

.. math::

   e' = \frac{s + \text{shadow}}{0} = \infty

This occurs when:

1. All departments have zero wages (economically meaningless), OR
2. Only Department III has labor, AND ``g₃₃ = 0.0`` (all reproductive labor unwaged)

The Qualitative Shift
---------------------

The infinity is **not** an edge case to be "handled" - it represents a
**qualitative transformation** in the social relation of production.

The wage relation, despite being exploitative, contains a formal exchange:
labor-power for money. When wages reach zero, this exchange disappears entirely.
What remains is **direct appropriation** - the condition of slavery, serfdom,
or what MIM Prisons calls the relationship between oppressor and oppressed
nations.

.. important::

   Infinity signals that we have crossed from **EXPLOITATION** (wage relation)
   to **EXPROPRIATION** (pure extraction). This is a qualitative, not merely
   quantitative, transformation.

Historical Conditions of Infinite Exploitation
----------------------------------------------

The zero-wage condition describes historically common conditions:

.. list-table:: Conditions of Pure Extraction
   :header-rows: 1
   :widths: 25 40 35

   * - Condition
     - Historical Reality
     - Monetary Relation
   * - **Chattel Slavery**
     - Foundation of American primitive accumulation
     - None - pure extraction
   * - **Domestic Labor**
     - Housewives historically received zero wages
     - Mediated through male wage
   * - **Prison Labor**
     - 13th Amendment permits slavery as punishment
     - $0.00-$0.50/hour or nothing
   * - **Colonial Extraction**
     - Indigenous dispossession and forced labor
     - Tribute, not wages
   * - **Child Labor (Periphery)**
     - Children in mines, fields, factories
     - Subsistence or nothing

Federici's Insight: The Wage as Exception
-----------------------------------------

From *Caliban and the Witch*: The wage relation is built **on top of** unwaged
labor, not the other way around. The "normal" case of finite exploitation
(where workers receive *some* wage) is actually the **historical exception** -
a privilege granted primarily to white male workers in the imperial core.

The infinity isn't a mathematical curiosity - it's the formula correctly
expressing that **most labor under capitalism (and certainly under
colonialism/slavery) has been unwaged**.

Implementation Guidance
-----------------------

**Do NOT sanitize the infinity.** Clamping to an arbitrary maximum would be
ideological mystification - it would make slavery, prison labor, and unwaged
domestic work appear as merely "very high" exploitation rather than
qualitatively different conditions.

Instead, preserve the infinity and add semantic meaning:

.. code-block:: python

   @computed_field
   @property
   def is_pure_extraction(self) -> bool:
       """True when labor is appropriated without any wage relation.

       This condition describes slavery, prison labor, fully unwaged
       domestic work, and colonial extraction - historically the
       PRIMARY mode of labor appropriation under capitalism.
       """
       return self.monetized_v == 0.0

Downstream systems must handle infinity appropriately:

1. **Comparison:** ``float('inf') > any_finite_number`` (always True)
2. **Arithmetic:** ``float('inf') + x = float('inf')`` (absorbs finite values)
3. **Danger:** ``float('inf') - float('inf') = nan`` (undefined)
4. **Semantic:** Treat infinity as a "pure extraction mode" flag

Core-Periphery Symmetry
------------------------

The Fortunati rate going to infinity in the periphery (or domestic sphere) is
the mathematical inverse of the labor aristocracy in the core:

.. list-table:: Extraction Symmetry
   :header-rows: 1
   :widths: 25 35 40

   * - Location
     - Wage/Value Relation
     - Exploitation Rate
   * - **Core**
     - ``W > V`` (wages exceed value)
     - May be negative (net recipients of imperial rent)
   * - **Periphery**
     - ``W → 0`` (wages approach zero)
     - ``e' → ∞`` (pure extraction)

The labor aristocracy's privileged position is subsidized by the infinite
extraction occurring in the periphery and in the reproductive sphere.

Usage Example
=============

.. code-block:: python

   from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
   from babylon.models import Currency

   # Create a tensor with partial shadow labor visibility
   tensor = ValueTensor4x3(
       fips_code="26163",  # Wayne County (Detroit)
       year=2022,
       dept_I=DepartmentRow(c=300.0, v=100.0, s=200.0),
       dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
       dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
       dept_III=DepartmentRow(c=50.0, v=100.0, s=70.0),
       naics_granularity=0.85,
       excluded_wages=50000.0,
       visibility_g33=0.3,  # 30% monetized, 70% shadow
   )

   # Compare standard vs Fortunati exploitation
   standard_rate = tensor.total_s / tensor.total_v
   fortunati_rate = tensor.exploitation_rate_fortunati

   print(f"Standard rate:  {standard_rate:.2%}")
   print(f"Fortunati rate: {fortunati_rate:.2%}")
   print(f"Shadow subsidy: ${tensor.shadow_subsidy:,.2f}")

   # Check for pure extraction
   if tensor.exploitation_rate_fortunati == float('inf'):
       print("WARNING: Pure extraction detected (no wages paid)")

See Also
========

- :ref:`imperial-rent` - Imperial rent extraction parallels shadow labor extraction
- :ref:`survival-calculus` - How material conditions affect revolutionary potential
- :ref:`theory` - MLM-TW theoretical foundation
- ``ai/shadow-labor-spec.yaml`` - Machine-readable specification
- ``ai/marxian-tensor-spec.yaml`` - Tensor specification
