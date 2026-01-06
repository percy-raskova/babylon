Survival Calculus
=================

The survival calculus models how agents make decisions based on their
perceived probability of survival under different strategies.

Core Principle
--------------

Agents act to maximize their probability of survival P(S). They choose
between two primary strategies:

1. **Acquiescence** - Working within the existing system
2. **Revolution** - Attempting to overturn the system

Survival by Acquiescence
------------------------

The probability of survival by acquiescence P(S|A) is modeled as:

.. math::

   P(S|A) = \text{Sigmoid}(W - S_{min})

Where:

- W = Current wealth
- S_min = Subsistence threshold

When wealth is well above subsistence, acquiescence offers high survival
probability. As wealth approaches subsistence, this probability drops.

Survival by Revolution
----------------------

The probability of survival by revolution P(S|R) is:

.. math::

   P(S|R) = \frac{O}{R}

Where:

- O = Organization (class solidarity, unions, parties)
- R = Repression (state capacity for violence)

Rupture Condition
-----------------

A **Rupture Event** (revolutionary moment) occurs when:

.. math::

   P(S|R) > P(S|A)

This happens when the system can no longer provide survival through
normal channels, AND revolutionary organization exceeds repressive capacity.

Loss Aversion
-------------

The model incorporates loss aversion - agents weight potential losses
more heavily than equivalent gains. This creates a bias toward acquiescence
that must be overcome by significant material degradation.

Material Basis of Survival
--------------------------

While the calculus above describes *decisions*, the **Vitality System**
enforces the biological constraints of those decisions. It operates in a
strict three-phase materialist causality chain:

1. **Phase 1: The Drain** (Subsistence Burn)
   Wealth is consumed based on population size and subsistence multipliers.

   .. math::

      Cost = (S_{base} \times Population) \times \mu_{subsistence}

2. **Phase 2: Grinding Attrition** (Inequality Mortality)
   When wealth is insufficient, the "Mass Line" coverage ratio determines
   mortality. High inequality increases the wealth threshold needed to
   prevent death.

   .. math::

      Threshold = 1.0 + Inequality

      Deficit = \max(0, Threshold - \frac{Wealth}{Needs})

      Deaths = Population \times (Deficit \times (0.5 + Inequality))

3. **Phase 3: The Reaper** (Extinction Check)
   Entities with zero population or those trapped in a "zombie state"
   (population=1 but starving) are marked inactive.

This system ensures that bad survival strategies result in physical
elimination, not just poor scores.

Implementation
--------------

See the survival formulas in :py:mod:`babylon.systems.formulas`:

- :py:func:`~babylon.systems.formulas.calculate_acquiescence_probability`
- :py:func:`~babylon.systems.formulas.calculate_revolution_probability`
- :py:func:`~babylon.systems.formulas.calculate_crossover_threshold`

See Also
--------

- :doc:`/concepts/george-jackson-model` - Consciousness bifurcation
- :doc:`/concepts/imperial-rent` - Economic conditions affecting survival
- :doc:`/reference/formulas` - Complete formula reference with examples
