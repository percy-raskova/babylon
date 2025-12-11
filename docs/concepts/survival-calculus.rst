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
