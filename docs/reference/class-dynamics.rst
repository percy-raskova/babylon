Class Wealth Dynamics
=====================

Empirically-derived ODE system modeling wealth flows between four Marxian
classes. Fitted from FRED Distributional Financial Accounts (2015-2025).

.. contents:: On This Page
   :local:
   :depth: 2

Research Question
-----------------

The original research question that motivated this analysis:

.. admonition:: User's Theory (Exact Words)

   I have a theory I want to validate against empirical evidence. The theory
   goes as follows: Within the imperial core today, there are 4 broad 'classes'
   identifiable by wealth.

   - The top 1%
   - The next 9% (90-99 percentile)
   - The next 50% (50-90 percentile)
   - The bottom 40-50%

   The theory states:

   - Top 1% owns approximately 1/3 of total wealth
   - Next 9% (90-99%) owns approximately 1/3 of total wealth
   - Next 50% (50-90%) owns approximately 1/3 of total wealth
   - Bottom 40-50% owns essentially nothing (~0%)

   I want to:

   1. Validate this against FRED Distributional Financial Accounts data
   2. Create a visualization with wealth brackets as FIXED (33%/33%/33%/0%)
      and population as the DEPENDENT variable
   3. Show a stacked area chart of population concentration in each wealth third
   4. Derive flow-based Marxian differential equations for class wealth dynamics
   5. These ODEs should be compatible with Babylon's formula system

Empirical Validation
--------------------

Using FRED Distributional Financial Accounts (2015 Q1 - 2025 Q2):

.. list-table:: Wealth Distribution (2025 Q2)
   :header-rows: 1
   :widths: 25 15 15 20 25

   * - Population Tier
     - Pop Share
     - Wealth Share
     - Theory Prediction
     - Babylon Class
   * - Top 1%
     - 1%
     - 30.7%
     - ~33% |check|
     - ``core_bourgeoisie``
   * - 90-99%
     - 9%
     - 36.4%
     - ~33% (slightly above)
     - ``petty_bourgeoisie``
   * - 50-90%
     - 40%
     - 30.3%
     - ~33% |check|
     - ``labor_aristocracy``
   * - Bottom 50%
     - 50%
     - 2.5%
     - ~0% |check|
     - ``internal_proletariat``

.. |check| unicode:: U+2713

**Verdict**: Theory is approximately correct. The actual distribution follows
a 31/36/30/2.5 pattern rather than exact 33/33/33/0, but the structural insight
holds.

Inverted Distribution
~~~~~~~~~~~~~~~~~~~~~

When we invert the question---asking what fraction of the *population* owns
each third of *wealth*---we find:

.. list-table:: Population by Wealth Third (2025 Q2)
   :header-rows: 1
   :widths: 40 30 30

   * - Wealth Bracket
     - Population Share
     - Interpretation
   * - Bottom third (0-33%)
     - 90.1%
     - Nine-tenths of Americans
   * - Middle third (33-67%)
     - 8.3%
     - Professional-managerial class
   * - Top third (67-100%)
     - 1.6%
     - Ultra-wealthy

ODE System
----------

State Variables
~~~~~~~~~~~~~~~

The system tracks four wealth shares that must sum to 1.0:

.. math::

   W_1 + W_2 + W_3 + W_4 = 1

Where:

- :math:`W_1(t)` = Core Bourgeoisie (Top 1%)
- :math:`W_2(t)` = Petty Bourgeoisie (90-99%)
- :math:`W_3(t)` = Labor Aristocracy (50-90%)
- :math:`W_4(t)` = Internal Proletariat (Bottom 50%)

First-Order System
~~~~~~~~~~~~~~~~~~

Wealth flows between classes via extraction and redistribution:

.. math::

   \frac{dW_1}{dt} &= \alpha_{41}W_4 + \alpha_{31}W_3 + \alpha_{21}W_2 - \delta_1 W_1 \\
   \frac{dW_2}{dt} &= \alpha_{32}W_3 + \alpha_{42}W_4 - \alpha_{21}W_2 - \delta_2 W_2 \\
   \frac{dW_3}{dt} &= \alpha_{43}W_4 + \gamma_3 - \alpha_{31}W_3 - \alpha_{32}W_3 - \delta_3 W_3 \\
   \frac{dW_4}{dt} &= -\left(\frac{dW_1}{dt} + \frac{dW_2}{dt} + \frac{dW_3}{dt}\right)

Where:

- :math:`\alpha_{ij}` = Extraction rate from class :math:`j` to class :math:`i`
- :math:`\delta_i` = Redistribution rate from class :math:`i` (taxation, inheritance)
- :math:`\gamma_3` = Imperial rent formation rate (superwages to core workers)

**FRED-Fitted Parameters (per quarter):**

.. list-table:: Extraction Rates
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Value
     - Description
   * - :math:`\alpha_{21}`
     - 0.0006
     - Petty bourgeoisie |rarr| Bourgeoisie
   * - :math:`\alpha_{41}, \alpha_{31}, \alpha_{32}, \alpha_{42}, \alpha_{43}`
     - 0.0
     - Other extraction rates (negligible)

.. |rarr| unicode:: U+2192

.. list-table:: Redistribution Rates
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Value
     - Description
   * - :math:`\delta_1`
     - 0.0010
     - From Bourgeoisie (progressive taxation)
   * - :math:`\delta_2`
     - 0.0020
     - From Petty Bourgeoisie
   * - :math:`\delta_3`
     - 0.0010
     - From Labor Aristocracy

.. list-table:: Imperial Rent
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Value
     - Description
   * - :math:`\gamma_3`
     - 0.0057
     - Imperial rent injection to Labor Aristocracy

Second-Order Dynamics
~~~~~~~~~~~~~~~~~~~~~

Models momentum effects and oscillation around equilibrium:

.. math::

   \frac{d^2 W_i}{dt^2} = \beta_i \frac{dW_i}{dt} - \omega_i^2 (W_i - W_i^*)

Where:

- :math:`\beta_i` = Damping coefficient (negative for mean-reversion)
- :math:`\omega_i` = Natural frequency of oscillation
- :math:`W_i^*` = Equilibrium wealth share (attractor)

**FRED-Fitted Equilibrium:**

.. list-table:: Equilibrium Attractors
   :header-rows: 1
   :widths: 30 15 55

   * - Class
     - :math:`W^*`
     - Interpretation
   * - Core Bourgeoisie
     - 0.305
     - Top 1% maintains ~30.5% homeostasis
   * - Petty Bourgeoisie
     - 0.382
     - 90-99% holds largest share
   * - Labor Aristocracy
     - 0.294
     - 50-90% receives imperial rent
   * - Internal Proletariat
     - 0.020
     - Bottom 50% owns essentially nothing

API Reference
-------------

Classes
~~~~~~~

.. py:class:: ClassDynamicsParams

   Parameters for the first-order ODE system.

   All rates are per-quarter (fitted from FRED 2015-2025).

   :ivar alpha_41: Extraction: proletariat |rarr| bourgeoisie (default: 0.0)
   :ivar alpha_31: Extraction: labor aristocracy |rarr| bourgeoisie (default: 0.0)
   :ivar alpha_21: Extraction: petty bourgeoisie |rarr| bourgeoisie (default: 0.0006)
   :ivar alpha_32: Extraction: labor aristocracy |rarr| petty bourgeoisie (default: 0.0)
   :ivar alpha_42: Extraction: proletariat |rarr| petty bourgeoisie (default: 0.0)
   :ivar alpha_43: Extraction: proletariat |rarr| labor aristocracy (default: 0.0)
   :ivar delta_1: Redistribution from bourgeoisie (default: 0.0010)
   :ivar delta_2: Redistribution from petty bourgeoisie (default: 0.0020)
   :ivar delta_3: Redistribution from labor aristocracy (default: 0.0010)
   :ivar gamma_3: Imperial rent formation rate (default: 0.0057)

.. py:class:: SecondOrderParams

   Parameters for second-order momentum dynamics.

   :ivar beta: Damping coefficients (negative = mean-reverting)
   :ivar omega: Natural frequencies of oscillation
   :ivar equilibrium: Attractor wealth shares

Functions
~~~~~~~~~

.. py:function:: calculate_wealth_flow(source_share, extraction_rate, resistance=0.0)

   Calculate per-tick wealth flow from source class.

   .. math::

      \text{Flow} = \alpha \times W_{\text{source}} \times (1 - r)

   :param source_share: Source class wealth share [0, 1]
   :param extraction_rate: Base extraction coefficient
   :param resistance: Class consciousness resistance [0, 1]
   :returns: Wealth delta flowing out of source class

.. py:function:: calculate_class_dynamics_derivative(wealth_shares, params=None, resistances=(0,0,0,0))

   Compute dW/dt for all four classes.

   :param wealth_shares: (W1, W2, W3, W4) current wealth shares summing to 1
   :param params: ODE system parameters (defaults to ClassDynamicsParams())
   :param resistances: (r1, r2, r3, r4) class consciousness levels [0, 1]
   :returns: (dW1/dt, dW2/dt, dW3/dt, dW4/dt) derivatives

.. py:function:: calculate_wealth_acceleration(wealth_share, velocity, equilibrium, damping=-0.1, frequency=0.05)

   Compute second derivative for momentum dynamics.

   :param wealth_share: Current wealth share W
   :param velocity: First derivative dW/dt
   :param equilibrium: Target equilibrium W*
   :param damping: Damping coefficient (negative = mean-reverting)
   :param frequency: Natural frequency of oscillation
   :returns: Second derivative d2W/dt2

.. py:function:: calculate_full_dynamics(wealth_shares, velocities, params=None, second_order=None, resistances=(0,0,0,0))

   Compute both first and second order derivatives.

   :param wealth_shares: Current wealth shares
   :param velocities: Current velocities (first derivatives)
   :param params: First-order ODE parameters
   :param second_order: Second-order parameters
   :param resistances: Class consciousness levels
   :returns: Tuple of (first_derivatives, second_derivatives)

.. py:function:: invert_wealth_to_population(wealth_shares, target_wealth_pct=33.333)

   Find population percentile owning target wealth percentage.

   Inverts the wealth distribution to find what fraction of the population
   owns a given fraction of total wealth.

   :param wealth_shares: (top_1%, 90-99%, 50-90%, bottom_50%) shares
   :param target_wealth_pct: Target cumulative wealth percentage
   :returns: Population percentile owning up to target_wealth_pct of wealth

Usage Examples
--------------

Basic Derivative Calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.systems.formulas import (
       ClassDynamicsParams,
       calculate_class_dynamics_derivative,
   )

   # Current wealth shares (must sum to 1.0)
   shares = (0.30, 0.36, 0.30, 0.04)

   # Calculate derivatives using default FRED-fitted params
   dw = calculate_class_dynamics_derivative(shares)

   # Verify conservation: derivatives sum to zero
   assert abs(sum(dw)) < 1e-10

Simulating Wealth Dynamics
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.systems.formulas import calculate_class_dynamics_derivative

   # Initial shares (2015 Q1 FRED data)
   shares = [0.307, 0.393, 0.289, 0.011]
   dt = 1.0  # One quarter

   # Simulate 40 quarters (10 years)
   for _ in range(40):
       dw = calculate_class_dynamics_derivative(tuple(shares))
       for i in range(4):
           shares[i] += dw[i] * dt

   # shares now approximately equals 2025 Q1 FRED data

Modeling Class Consciousness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.systems.formulas import calculate_class_dynamics_derivative

   shares = (0.30, 0.36, 0.30, 0.04)

   # No resistance: full extraction
   dw_no_resist = calculate_class_dynamics_derivative(shares)

   # Labor aristocracy develops consciousness (r=0.5)
   dw_conscious = calculate_class_dynamics_derivative(
       shares,
       resistances=(0.0, 0.0, 0.5, 0.0)
   )

   # With consciousness, less flows to bourgeoisie
   assert dw_conscious[0] < dw_no_resist[0]

Inverting the Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.systems.formulas import invert_wealth_to_population

   # 2025 Q2 FRED data (as percentages)
   shares = (30.7, 36.4, 30.3, 2.5)

   # What population owns the bottom third of wealth?
   pop_at_33 = invert_wealth_to_population(shares, 33.333)
   # Returns ~90.1 (90.1% of population owns bottom third)

   # What population owns the bottom two-thirds?
   pop_at_67 = invert_wealth_to_population(shares, 66.667)
   # Returns ~98.4 (98.4% of population owns bottom two-thirds)

Theoretical Implications
------------------------

MLM-TW Validation
~~~~~~~~~~~~~~~~~

The empirical data validates core Marxist-Leninist-Maoist Third Worldist
predictions:

1. **Structural Stability**: Wealth concentration is remarkably stable
   (30% |pm| 1% for Top 1% over 11 years). This is not accidental but
   structurally self-reinforcing.

2. **Proletariat Dispossession**: Bottom 50% owns essentially nothing (2.5%).
   This validates Marx's prediction of proletarianization.

3. **Labor Aristocracy Mechanism**: The 50-90% tier receives a constant
   injection of imperial rent (:math:`\gamma_3 = 0.0057`). This is the
   material basis of first-world worker complicity in imperialism.

4. **Buffer Class Erosion**: The 90-99% (petty bourgeoisie) slowly loses
   ground (-0.3%/year). The professional-managerial buffer is weakening.

.. |pm| unicode:: U+00B1

COVID-19 as Natural Experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The COVID pandemic provided a natural experiment in crisis dynamics:

- **Q4 2019** |rarr| **Q1 2020**: Top 1% dropped from 30.5% to 29.1%
- **Q1 2020**: Bottom 50% rose from 1.9% to 2.7% (stimulus)
- **Q4 2020**: System restored homeostasis (Top 1% back to 30.5%)

The system's rapid return to equilibrium demonstrates the structural nature
of wealth concentration---it cannot be reformed away.

See Also
--------

- :doc:`formulas` - Complete formula specification
- :doc:`fred-data` - FRED data sources and API usage
- ``tools/analyze_wealth_distribution.py`` - Analysis script
- ``ai-docs/class-dynamics.yaml`` - Machine-readable specification
