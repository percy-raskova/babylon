Formulas Reference
==================

Complete specification of mathematical formulas used in the Babylon
simulation engine. All formulas are implemented in
:py:mod:`babylon.systems.formulas`.

Constants
---------

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Constant
     - Value
     - Description
   * - ``LOSS_AVERSION_COEFFICIENT``
     - 2.25
     - Kahneman-Tversky loss aversion multiplier
   * - ``EPSILON``
     - 1e-6
     - Small value to prevent division by zero

Imperial Rent Formulas
----------------------

Core Extraction Formula
~~~~~~~~~~~~~~~~~~~~~~~

Calculates value extracted from periphery to core:

.. math::

   \Phi(W_p, \Psi_p) = \alpha \times W_p \times (1 - \Psi_p)

Where:

- :math:`\Phi` = Imperial rent extracted
- :math:`\alpha` = Extraction efficiency coefficient [0, 1]
- :math:`W_p` = Periphery wage share [0, 1]
- :math:`\Psi_p` = Periphery consciousness (0 = submissive, 1 = revolutionary)

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_imperial_rent

   rent = calculate_imperial_rent(
       alpha=0.8,
       periphery_wages=0.3,
       periphery_consciousness=0.2
   )  # Returns 0.192

Labor Aristocracy Ratio
~~~~~~~~~~~~~~~~~~~~~~~

Determines if workers receive more than value produced:

.. math::

   \text{LA Ratio} = \frac{W_c}{V_c}

When ratio > 1, the class is **labor aristocracy** (benefiting from imperial rent).

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import (
       calculate_labor_aristocracy_ratio,
       is_labor_aristocracy,
   )

   ratio = calculate_labor_aristocracy_ratio(
       core_wages=120.0,
       value_produced=100.0
   )  # Returns 1.2

   is_la = is_labor_aristocracy(
       core_wages=120.0,
       value_produced=100.0
   )  # Returns True

Consciousness Formulas
----------------------

Consciousness Drift
~~~~~~~~~~~~~~~~~~~

Models ideological change based on material conditions:

.. math::

   \frac{d\Psi_c}{dt} = k(1 - \frac{W_c}{V_c}) - \lambda\Psi_c

Where:

- :math:`\Psi_c` = Current consciousness level
- :math:`k` = Drift sensitivity coefficient
- :math:`W_c` = Core wages
- :math:`V_c` = Value produced
- :math:`\lambda` = Decay coefficient

**Fascist Bifurcation Extension:**

When wages are falling (``wage_change < 0``), agitation energy is calculated:

.. math::

   E_{agitation} = |W_{change}| \times \lambda_{loss}

Where :math:`\lambda_{loss} = 2.25` (loss aversion coefficient).

This energy routes based on solidarity:

- **With solidarity** (``solidarity_pressure > 0``): Energy adds to drift (revolutionary)
- **Without solidarity** (``solidarity_pressure = 0``): Energy subtracts from drift (fascist)

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_consciousness_drift

   drift = calculate_consciousness_drift(
       core_wages=80.0,
       value_produced=100.0,
       current_consciousness=0.5,
       sensitivity_k=0.1,
       decay_lambda=0.05,
       solidarity_pressure=0.8,
       wage_change=-10.0
   )

Ideological Routing
~~~~~~~~~~~~~~~~~~~

Multi-dimensional consciousness routing from crisis conditions (George Jackson analysis):

.. math::

   E_{agitation} = |W_{change}| \times \lambda_{loss} + |X_{change}| \times \lambda_{loss}

Where:

- :math:`W_{change}` = Wage change (negative = crisis)
- :math:`X_{change}` = Wealth change (negative = extraction)
- :math:`\lambda_{loss} = 2.25` (loss aversion coefficient)

Routing based on solidarity infrastructure:

- **High solidarity** + material loss → Class consciousness increases (revolutionary)
- **Low solidarity** + material loss → National identity increases (fascist)

Historical examples: Germany 1933 (crisis + atomization → fascism) vs
Russia 1917 (crisis + organization → revolution).

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_ideological_routing

   new_class, new_nation, new_agitation = calculate_ideological_routing(
       wage_change=-20.0,
       wealth_change=-10.0,  # Wealth extraction compounds crisis
       solidarity_pressure=0.9,
       current_class_consciousness=0.5,
       current_national_identity=0.5,
       current_agitation=0.0,
       agitation_decay=0.1
   )
   # High solidarity routes agitation to class consciousness

Survival Calculus Formulas
--------------------------

Acquiescence Probability
~~~~~~~~~~~~~~~~~~~~~~~~

Probability of survival through compliance with the system:

.. math::

   P(S|A) = \frac{1}{1 + e^{-k(W - S_{min})}}

Where:

- :math:`W` = Current wealth
- :math:`S_{min}` = Subsistence threshold
- :math:`k` = Curve steepness

At the threshold (W = S_min), probability is exactly 0.5.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_acquiescence_probability

   prob = calculate_acquiescence_probability(
       wealth=100.0,
       subsistence_threshold=100.0,
       steepness_k=0.1
   )  # Returns 0.5 (at threshold)

Revolution Probability
~~~~~~~~~~~~~~~~~~~~~~

Probability of survival through collective action:

.. math::

   P(S|R) = \frac{O}{R + \epsilon}

Where:

- :math:`O` = Organization/cohesion level [0, 1]
- :math:`R` = State repression capacity [0, 1]
- :math:`\epsilon` = Small constant preventing division by zero

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_revolution_probability

   prob = calculate_revolution_probability(
       cohesion=0.8,
       repression=0.2
   )  # Returns 1.0 (clamped)

Rupture Condition
~~~~~~~~~~~~~~~~~

A **Rupture Event** occurs when:

.. math::

   P(S|R) > P(S|A)

This is the **crossover threshold** - the wealth level where revolution
becomes a rational survival strategy.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_crossover_threshold

   threshold = calculate_crossover_threshold(
       cohesion=0.6,
       repression=0.4,
       subsistence_threshold=100.0,
       steepness_k=0.1
   )

Loss Aversion
~~~~~~~~~~~~~

Applies Kahneman-Tversky loss aversion (losses weighted 2.25x):

.. math::

   V_{perceived} = \begin{cases}
   V & \text{if } V \geq 0 \\
   2.25 \times V & \text{if } V < 0
   \end{cases}

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import apply_loss_aversion

   perceived_gain = apply_loss_aversion(100.0)   # Returns 100.0
   perceived_loss = apply_loss_aversion(-100.0)  # Returns -225.0

Unequal Exchange Formulas
-------------------------

Exchange Ratio
~~~~~~~~~~~~~~

Quantifies value extraction via trade:

.. math::

   \rho = \frac{L_p}{L_c} \times \frac{W_c}{W_p}

Where:

- :math:`\rho` = Exchange ratio (uses rho to avoid collision with epsilon constant)
- :math:`L_p` = Periphery labor hours
- :math:`L_c` = Core labor hours (same product)
- :math:`W_c` = Core wage rate
- :math:`W_p` = Periphery wage rate

When :math:`\rho > 1`, periphery gives more value than it receives.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_exchange_ratio

   ratio = calculate_exchange_ratio(
       periphery_labor_hours=100.0,
       core_labor_hours=100.0,
       core_wage=20.0,
       periphery_wage=5.0
   )  # Returns 4.0

Exploitation Rate
~~~~~~~~~~~~~~~~~

Converts exchange ratio to percentage:

.. math::

   \text{Exploitation Rate} = (\rho - 1) \times 100\%

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_exploitation_rate

   rate = calculate_exploitation_rate(exchange_ratio=4.0)  # Returns 300.0

Value Transfer
~~~~~~~~~~~~~~

Calculates actual value transferred:

.. math::

   \text{Transfer} = V_{production} \times (1 - \frac{1}{\rho})

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_value_transfer

   transfer = calculate_value_transfer(
       production_value=1000.0,
       exchange_ratio=4.0
   )  # Returns 750.0

Prebisch-Singer Effect
~~~~~~~~~~~~~~~~~~~~~~

Models terms of trade decline for commodity exporters:

.. math::

   P_{new} = P_{initial} \times (1 + \eta \times \Delta Q)

Where :math:`\eta` is price elasticity (typically negative).

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import prebisch_singer_effect

   new_price = prebisch_singer_effect(
       initial_price=100.0,
       production_increase=0.2,
       elasticity=-0.5
   )  # Returns 90.0

Solidarity Transmission
-----------------------

Models consciousness transmission via solidarity edges:

.. math::

   \Delta\Psi_{target} = \sigma \times (\Psi_{source} - \Psi_{target})

Where:

- :math:`\sigma` = Solidarity strength on edge [0, 1]
- :math:`\Psi_{source}` = Source consciousness (periphery)
- :math:`\Psi_{target}` = Target consciousness (core)

Transmission only occurs if ``source_consciousness > activation_threshold``.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_solidarity_transmission

   delta = calculate_solidarity_transmission(
       source_consciousness=0.8,
       target_consciousness=0.2,
       solidarity_strength=0.5,
       activation_threshold=0.3
   )  # Returns 0.3

Territory Heat Formulas
-----------------------

Heat Accumulation
~~~~~~~~~~~~~~~~~

Territories accumulate heat from high-profile activities:

.. math::

   H_{t+1} = H_t + \Delta H_{activity} - \Delta H_{decay}

.. list-table:: Heat Thresholds
   :header-rows: 1
   :widths: 20 80

   * - Heat Level
     - Consequence
   * - < 0.4
     - Normal operations
   * - 0.4 - 0.8
     - Increased surveillance
   * - >= 0.8
     - **Eviction trigger** - classes must relocate

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Effect
   * - ``territory.heat_threshold``
     - 0.8
     - Heat level triggering eviction
   * - ``territory.heat_decay``
     - 0.1
     - Heat reduction per tick
   * - ``territory.spillover_coefficient``
     - 0.2
     - Heat transferred on displacement

Dynamic Balance (Bourgeoisie Decision)
--------------------------------------

Models bourgeoisie policy decisions based on imperial rent pool and tension:

.. list-table:: Decision Matrix
   :header-rows: 1
   :widths: 30 35 35

   * - Condition
     - Decision
     - Effect
   * - pool >= 0.7, tension < 0.3
     - BRIBERY
     - wages +5%
   * - pool < 0.1
     - CRISIS
     - wages -15%, repression +20%
   * - pool < 0.3, tension > 0.5
     - IRON_FIST
     - repression +10%
   * - pool < 0.3, tension <= 0.5
     - AUSTERITY
     - wages -5%
   * - else
     - NO_CHANGE
     - status quo

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_bourgeoisie_decision

   decision, wage_delta, repression_delta = calculate_bourgeoisie_decision(
       pool_ratio=0.8,
       aggregate_tension=0.2
   )  # Returns ("bribery", 0.05, 0.0)

Metabolic Rift Formulas
-----------------------

Ecological limits on capital accumulation (Slice 1.4).

Biocapacity Delta
~~~~~~~~~~~~~~~~~

Models change in ecological carrying capacity:

.. math::

   \Delta B = R - (E \times \eta)

Where:

- :math:`R` = Regeneration (fraction of max restored per tick)
- :math:`E` = Extraction intensity × current biocapacity
- :math:`\eta` = Entropy factor (waste multiplier, typically 1.2)

When :math:`\Delta B < 0`, the system is depleting faster than regenerating.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_biocapacity_delta

   delta = calculate_biocapacity_delta(
       regeneration_rate=0.02,   # 2% max restored per tick
       max_biocapacity=100.0,
       extraction_intensity=0.05,
       current_biocapacity=50.0,
       entropy_factor=1.2
   )  # Returns -1.0 (depletion)

Overshoot Ratio
~~~~~~~~~~~~~~~

Measures ecological overshoot:

.. math::

   O = \frac{C}{B}

Where:

- :math:`C` = Total consumption across all entities
- :math:`B` = Total biocapacity available

When :math:`O > 1.0`, the system is in ecological overshoot (consuming more
than the planet can regenerate).

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_overshoot_ratio

   ratio = calculate_overshoot_ratio(
       total_consumption=200.0,
       total_biocapacity=100.0
   )  # Returns 2.0 (2x overshoot)

Vitality Formulas
-----------------

Mortality rate calculations for population attrition (Mass Line Refactor Phase 3).

Mortality Rate (Coverage Ratio Threshold)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calculates population attrition based on wealth coverage and inequality:

.. math::

   \text{coverage\_ratio} = \frac{W_{pc}}{S}

   \text{threshold} = 1 + I

   \text{attrition\_rate} = \begin{cases}
   0 & \text{if coverage\_ratio} \geq \text{threshold} \\
   (\text{threshold} - \text{coverage\_ratio}) \times (0.5 + I) & \text{otherwise}
   \end{cases}

Where:

- :math:`W_{pc}` = Wealth per capita
- :math:`S` = Subsistence needs (s_bio + s_class)
- :math:`I` = Inequality coefficient [0, 1]

**Mechanic:** High inequality raises the survival floor, causing mortality
even when average wealth appears sufficient. This models how wealth
concentration exposes marginal workers to attrition.

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_mortality_rate

   attrition = calculate_mortality_rate(
       wealth_per_capita=0.5,
       subsistence_needs=0.4,
       inequality=0.3
   )  # Returns attrition rate [0, 1]

TRPF Formulas (Tendency of the Rate of Profit to Fall)
------------------------------------------------------

Marx's rate of profit formulas (Capital Vol. 3). Currently used as surrogate
for organic composition via extraction efficiency decay.

TRPF Multiplier (Surrogate)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Models declining extraction efficiency over time:

.. math::

   \text{multiplier} = \max(\text{floor}, 1 - (\text{coefficient} \times \text{tick}))

Where:

- :math:`\text{coefficient}` = TRPF decay rate (default 0.0005)
- :math:`\text{floor}` = Minimum efficiency (default 0.1)

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_trpf_multiplier

   mult = calculate_trpf_multiplier(
       tick=1000,
       trpf_coefficient=0.0005,
       floor=0.1
   )  # Returns 0.5

Rent Pool Decay
~~~~~~~~~~~~~~~

Models imperial rent pool depletion:

.. math::

   \text{new\_pool} = \text{current\_pool} \times (1 - \text{decay\_rate})

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_rent_pool_decay

   new_pool = calculate_rent_pool_decay(
       current_pool=100.0,
       decay_rate=0.002
   )  # Returns 99.8

Rate of Profit (Epoch 2 Placeholder)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Full Marx formula for rate of profit:

.. math::

   r = \frac{s}{c + v}

Where:

- :math:`s` = Surplus value
- :math:`c` = Constant capital (machinery, materials)
- :math:`v` = Variable capital (wages)

**Implementation:**

.. code-block:: python

   from babylon.systems.formulas import calculate_rate_of_profit

   rate = calculate_rate_of_profit(
       surplus_value=100.0,
       constant_capital=200.0,
       variable_capital=100.0
   )  # Returns 0.333

Organic Composition (Epoch 2 Placeholder)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ratio of constant to variable capital:

.. math::

   \text{OCC} = \frac{c}{v}

Rising OCC is the mechanism behind the tendential fall in profit rate.

Formula-to-System Mapping
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Formula
     - System
     - Module
   * - Mortality Rate (Coverage Ratio)
     - VitalitySystem
     - ``engine/systems/vitality.py``
   * - Production (Labor × Biocapacity)
     - ProductionSystem
     - ``engine/systems/production.py``
   * - Imperial Rent
     - ImperialRentSystem
     - ``engine/systems/economic.py``
   * - TRPF Multiplier
     - ImperialRentSystem
     - ``engine/systems/economic.py``
   * - Rent Pool Decay
     - ImperialRentSystem
     - ``engine/systems/economic.py``
   * - Consciousness Drift
     - ConsciousnessSystem
     - ``engine/systems/ideology.py``
   * - Ideological Routing
     - ConsciousnessSystem
     - ``engine/systems/ideology.py``
   * - Survival Calculus
     - SurvivalSystem
     - ``engine/systems/survival.py``
   * - Solidarity Transmission
     - SolidaritySystem
     - ``engine/systems/solidarity.py``
   * - Territory Heat
     - TerritorySystem
     - ``engine/systems/territory.py``
   * - Bourgeoisie Decision
     - ContradictionSystem
     - ``engine/systems/contradiction.py``
   * - LA Decomposition (15%/85% split)
     - DecompositionSystem
     - ``engine/systems/decomposition.py``
   * - Control Ratio (Guard:Prisoner)
     - ControlRatioSystem
     - ``engine/systems/control_ratio.py``
   * - Metabolic Rift
     - MetabolismSystem
     - ``engine/systems/metabolism.py``

See Also
--------

- :doc:`/concepts/imperial-rent` - Theoretical explanation of imperial rent
- :doc:`/concepts/survival-calculus` - Survival decision model
- :doc:`/concepts/george-jackson-model` - Consciousness bifurcation theory
- :doc:`/concepts/carceral-geography` - Territory and heat dynamics
- :doc:`/reference/systems` - Systems that use these formulas
- :py:mod:`babylon.systems.formulas` - Source code
