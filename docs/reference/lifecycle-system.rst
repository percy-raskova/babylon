Lifecycle System Reference
==========================

API reference for the D-P-D' lifecycle circuit (Feature 030).

The lifecycle system tracks intergenerational class reproduction through
population cohort dynamics, legitimation indices, Pareto-distributed
inheritance, Chetty-calibrated class mobility, and ideology transmission.
It executes per-tick on territory nodes, writing population state and
legitimation metrics to the simulation graph.

.. contents:: On this page
   :local:
   :depth: 2

Enums
-----

LegitimationClassification
~~~~~~~~~~~~~~~~~~~~~~~~~~

Crisis regime classification for the legitimation index.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Value
     - Threshold
     - Description
   * - ``CRISIS``
     - index < 0.3
     - D' promise not credible. Agitation routes to bifurcation.
   * - ``UNSTABLE``
     - 0.3 <= index < 0.5
     - D' promise weakening. Risk accumulating.
   * - ``STABLE``
     - index >= 0.5
     - D' promise credible. Acquiescence maintained.

Defined in :py:class:`~babylon.models.enums.LegitimationClassification`.

EventTypes
~~~~~~~~~~

Five event types added to :py:class:`~babylon.models.enums.EventType`.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Event
     - Description
   * - ``LIFECYCLE_TRANSITION``
     - Population moved between phases (emitted every tick per territory).
   * - ``LEGITIMATION_CRISIS``
     - Legitimation classification changed to CRISIS.
   * - ``LEGITIMATION_RECOVERY``
     - Classification improved from CRISIS to STABLE.
   * - ``INHERITANCE_TRANSFER``
     - D' death triggered inheritance flow.
   * - ``DUAL_CIRCUIT_INTERFERENCE``
     - Resource competition or dispossession short-circuit detected.

Models
------

DPDState
~~~~~~~~

Frozen Pydantic model. Per-county population distribution across
lifecycle phases.

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Field
     - Type
     - Default
     - Description
   * - ``pop_d``
     - float
     - *required*
     - Population in D phase (pre-productive). >= 0.
   * - ``pop_p``
     - float
     - *required*
     - Population in P phase (productive). >= 0.
   * - ``pop_d_prime``
     - float
     - *required*
     - Population in D' phase (post-productive). >= 0.
   * - ``rate_d_to_p``
     - float
     - *required*
     - Annual transition rate D to P. [0, 1].
   * - ``rate_p_to_d_prime``
     - float
     - *required*
     - Annual transition rate P to D'. [0, 1].
   * - ``rate_d_prime_to_death``
     - float
     - *required*
     - Annual mortality rate in D'. [0, 1].
   * - ``birth_rate``
     - float
     - *required*
     - Births per P-phase person per tick. [0, 1].
   * - ``wealth_d_prime``
     - Currency
     - 0.0
     - Aggregate wealth held by D' cohort.

**Computed properties:**

- ``total_population`` -- Sum of all three phase populations.
- ``dependency_ratio`` -- ``(pop_d + pop_d_prime) / pop_p``.
  Returns ``inf`` if ``pop_p`` is zero.

Defined in :py:class:`~babylon.economics.lifecycle.types.DPDState`.

LegitimationState
~~~~~~~~~~~~~~~~~

Frozen Pydantic model. Weighted legitimation index components per county.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Type
     - Description
   * - ``pension_coverage``
     - Probability
     - Fraction of P-phase with pension access.
   * - ``ss_replacement_rate``
     - Probability
     - Social Security replacement ratio.
   * - ``healthcare_security``
     - Probability
     - Fraction with secure D' healthcare.
   * - ``home_ownership_rate``
     - Probability
     - P-phase home ownership rate.
   * - ``retirement_confidence``
     - Probability
     - Subjective D' security assessment.

All fields required. No defaults.

Defined in :py:class:`~babylon.economics.lifecycle.types.LegitimationState`.

InheritanceFlow
~~~~~~~~~~~~~~~

Frozen Pydantic model. Intergenerational wealth transfer at D' terminus.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``total_transferred``
     - Currency
     - Total wealth transferred at D' death.
   * - ``care_consumed``
     - Currency
     - Wealth consumed by end-of-life care costs.
   * - ``net_inheritance``
     - Currency
     - Net inheritance (total minus care costs).
   * - ``inheritance_gini``
     - Gini
     - Gini coefficient of inheritance distribution.

**Validation:** ``care_consumed`` cannot exceed ``total_transferred``.

Defined in :py:class:`~babylon.economics.lifecycle.types.InheritanceFlow`.

ClassMobilityParams
~~~~~~~~~~~~~~~~~~~

Frozen Pydantic model. Chetty-derived class mobility parameters
per county. Static after initialization; read-only during simulation.

.. list-table::
   :header-rows: 1
   :widths: 30 10 10 50

   * - Field
     - Type
     - Default
     - Description
   * - ``mobility_base_rate``
     - float
     - 0.445
     - KFR pooled at P25 (Chetty Opportunity Atlas).
   * - ``mobility_base_rate_p75``
     - float
     - 0.580
     - KFR pooled at P75.
   * - ``mobility_racial_gap``
     - float
     - 0.134
     - Black-White KFR gap at P25.
   * - ``carceral_modifier``
     - float
     - 2.8
     - Incarceration rate multiplier on P to D' transition. [0, 10].
   * - ``early_mortality_modifier``
     - float
     - 1.24
     - Premature death multiplier on P to D' transition. [0, 10].
   * - ``baseline_gini``
     - Gini
     - 0.485
     - County Gini coefficient (Chetty Table 8).
   * - ``poverty_share``
     - Probability
     - 0.126
     - Fraction below poverty line.
   * - ``employment_rate``
     - Probability
     - 0.60
     - Employment-to-population ratio.
   * - ``single_parent_fraction``
     - Probability
     - 0.234
     - Single-parent household share.
   * - ``college_rate``
     - Probability
     - 0.33
     - College graduation rate.

**Validation:** ``mobility_base_rate_p75 >= mobility_base_rate``;
``mobility_racial_gap <= mobility_base_rate``.

Defined in :py:class:`~babylon.economics.lifecycle.types.ClassMobilityParams`.

Formulas
--------

Six pure functions in :py:mod:`babylon.formulas.lifecycle`.

compute_population_flow
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_population_flow(
       *, pop_d: float, pop_p: float, pop_d_prime: float,
       birth_rate: float, rate_d_to_p: float,
       rate_p_to_d_prime: float, rate_d_prime_to_death: float,
   ) -> tuple[float, float, float, float, float]

Computes one-tick population transitions. Returns
``(new_pop_d, new_pop_p, new_pop_d_prime, births, deaths)``.
All outputs clamped to non-negative.

.. math::

   \text{births} &= \text{birth\_rate} \times \text{pop}_P \\
   \text{new}_D &= \text{pop}_D + \text{births} - \text{rate}_{D \to P} \times \text{pop}_D \\
   \text{new}_P &= \text{pop}_P + \text{rate}_{D \to P} \times \text{pop}_D - \text{rate}_{P \to D'} \times \text{pop}_P \\
   \text{new}_{D'} &= \text{pop}_{D'} + \text{rate}_{P \to D'} \times \text{pop}_P - \text{rate}_{D' \to \text{death}} \times \text{pop}_{D'}

compute_dependency_ratio
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_dependency_ratio(
       *, pop_d: float, pop_p: float, pop_d_prime: float,
   ) -> float

Returns ``(pop_d + pop_d_prime) / pop_p``, or ``inf`` if ``pop_p``
is zero.

compute_legitimation_index
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_legitimation_index(
       *, pension_coverage: float, ss_replacement_rate: float,
       healthcare_security: float, home_ownership_rate: float,
       retirement_confidence: float,
       w_home: float, w_health: float, w_retire: float,
       w_pension: float, w_ss: float,
   ) -> float

Weighted sum of five legitimation components, clamped to [0, 1].

.. math::

   L = w_h \cdot \text{home} + w_{hc} \cdot \text{health} + w_r \cdot \text{retire} + w_p \cdot \text{pension} + w_s \cdot \text{ss}

Default weights: 0.35, 0.30, 0.20, 0.10, 0.05.

compute_pareto_gini
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_pareto_gini(*, alpha: float) -> float

Computes Gini coefficient from Pareto shape parameter.

.. math::

   G = \frac{1}{2\alpha - 1}

Raises ``ValueError`` if ``alpha <= 0.5``.

compute_ideology_transmission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_ideology_transmission(
       *, caregiver_ideology: float, institutional_hegemony: float,
       caregiver_weight: float, institutional_weight: float,
   ) -> float

Blends caregiver and institutional influence for D-to-P ideology transfer.

.. math::

   I = w_c \cdot \text{caregiver} + w_i \cdot \text{institutional}

Default weights: caregiver 0.7, institutional 0.3.

compute_shadow_subsidy
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   compute_shadow_subsidy(
       *, p_g2_labor_value: float, wage_paid_for_d_g2: float,
   ) -> float

Returns the difference between next-generation labor value and wages
paid for child-rearing. Always >= 0.

Calculators
-----------

Four calculator protocols with default implementations following the
Protocol + Default pattern used across the economics module.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Protocol
     - Default Implementation
     - Purpose
   * - ``CohortDynamicsCalculator``
     - ``DefaultCohortDynamicsCalculator``
     - Population transitions, conservation, differential rates, ideology
   * - ``LegitimationCalculator``
     - ``DefaultLegitimationCalculator``
     - Legitimation index, blending, crisis classification
   * - ``InheritanceCalculator``
     - ``DefaultInheritanceCalculator``
     - Pareto inheritance, care costs, Gini computation
   * - ``ClassMobilityCalculator``
     - ``DefaultClassMobilityCalculator``
     - Premature exit rates, carceral/mortality modifiers

Defined in :py:mod:`babylon.economics.lifecycle`.

LifecycleSystem
---------------

Registered at position 7 in the system execution order, between
CommunitySystem (6) and SolidaritySystem (8).

**System name:** ``"lifecycle"``

**Module:** :py:mod:`babylon.engine.systems.lifecycle`

Step Phases
~~~~~~~~~~~

The ``step()`` method executes seven phases per territory node per tick:

1. **Read or initialize DPDState** from graph node. If absent,
   initializes from ``LifecycleDefines`` defaults using the territory's
   population attribute.

2. **Compute population transitions** via ``CohortDynamicsCalculator``.
   Applies birth, transition, and death rates. Verifies conservation
   invariant (< 0.1% drift).

3. **Compute legitimation index** from five material indicators.
   Classifies into CRISIS / UNSTABLE / STABLE. Emits
   ``LEGITIMATION_CRISIS`` or ``LEGITIMATION_RECOVERY`` events on
   state transitions.

4. **Compute inheritance flow** when D' deaths occur. Applies Pareto
   distribution and care cost fraction. Emits ``INHERITANCE_TRANSFER``
   event with transfer amounts and Gini.

5. **Compute ideology transmission** for the D-to-P cohort. Blends
   caregiver ideology with institutional hegemony, applies regression
   toward mean.

6. **Apply class mobility parameters** from Chetty data. Computes
   adjusted P-to-D' rate incorporating early mortality modifier.

7. **Apply differential rates** for structural inequality. Writes
   differential P-to-D' rate incorporating racial and carceral
   modifiers.

Graph Mutations
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Node
     - Attribute
     - Effect
   * - Territory
     - ``dpd_state``
     - Updated DPDState dict each tick.
   * - Territory
     - ``dependency_ratio``
     - ``(pop_d + pop_d_prime) / pop_p``.
   * - Territory
     - ``legitimation_index``
     - Weighted legitimation score [0, 1].
   * - Territory
     - ``legitimation_crisis``
     - LegitimationClassification value string.
   * - Territory
     - ``transmitted_ideology``
     - D-to-P ideology blend.
   * - Territory
     - ``mobility_params``
     - ClassMobilityParams dict.
   * - Territory
     - ``adjusted_p_to_d_prime``
     - P-to-D' rate with mortality modifier.
   * - Territory
     - ``differential_p_to_d_prime``
     - P-to-D' rate with racial + carceral modifiers.

Error Handling
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Condition
     - Response
   * - Missing DPDState on node
     - Initialize from LifecycleDefines defaults.
   * - Conservation violation > 0.1%
     - Log warning. Populations are not normalized.
   * - Negative population after transitions
     - Clamped to 0.0 by ``compute_population_flow``.
   * - Division by zero (pop_p = 0)
     - ``dependency_ratio`` returns ``inf``.

Configuration
~~~~~~~~~~~~~

``GameDefines.lifecycle`` provides all tuning coefficients via
:py:class:`~babylon.config.defines.LifecycleDefines` (36 parameters).

**Population Rates**

.. list-table::
   :header-rows: 1
   :widths: 30 10 15 45

   * - Parameter
     - Default
     - Source
     - Description
   * - ``birth_rate``
     - 0.0107
     - CDC NVSS 2023
     - Births per P-phase person per tick.
   * - ``rate_d_to_p``
     - 0.0556
     - Census
     - D to P transition (1/18 years).
   * - ``rate_p_to_d_prime``
     - 0.0213
     - Census
     - P to D' transition (1/47 years).
   * - ``rate_d_prime_to_death``
     - 0.039
     - CDC WONDER 2023
     - D' annual mortality.

**Initial Population Fractions**

.. list-table::
   :header-rows: 1
   :widths: 30 10 15 45

   * - Parameter
     - Default
     - Source
     - Description
   * - ``initial_pop_d_frac``
     - 0.215
     - Census 2024
     - Initial D phase fraction.
   * - ``initial_pop_p_frac``
     - 0.605
     - Census 2024
     - Initial P phase fraction.
   * - ``initial_pop_d_prime_frac``
     - 0.180
     - Census 2024
     - Initial D' phase fraction.

**Legitimation Weights**

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``legit_w_home_ownership``
     - 0.35
     - Rank 1. Home ownership weight.
   * - ``legit_w_healthcare_security``
     - 0.30
     - Rank 2. Healthcare security weight.
   * - ``legit_w_retirement_confidence``
     - 0.20
     - Rank 3. Retirement confidence weight.
   * - ``legit_w_pension_coverage``
     - 0.10
     - Rank 4. Pension coverage weight.
   * - ``legit_w_ss_replacement``
     - 0.05
     - Rank 5. SS replacement weight.

**Legitimation Thresholds**

.. list-table::
   :header-rows: 1
   :widths: 40 10 50

   * - Parameter
     - Default
     - Description
   * - ``legitimation_blend_weight``
     - 0.6
     - Structural vs agitation blend for bifurcation feed.
   * - ``legitimation_crisis_threshold``
     - 0.3
     - Index below this is CRISIS.
   * - ``legitimation_unstable_threshold``
     - 0.5
     - Index below this is UNSTABLE.

**Inheritance**

.. list-table::
   :header-rows: 1
   :widths: 30 10 15 45

   * - Parameter
     - Default
     - Source
     - Description
   * - ``pareto_alpha``
     - 1.5
     - Fed SCF
     - Pareto shape for wealth distribution.
   * - ``care_cost_fraction``
     - 0.4
     - --
     - Fraction of D' wealth consumed by care.

**Chetty Mobility**

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Parameter
     - Default
     - Description
   * - ``mobility_base_rate``
     - 0.445
     - KFR pooled at P25.
   * - ``mobility_base_rate_p75``
     - 0.580
     - KFR pooled at P75.
   * - ``mobility_racial_gap``
     - 0.134
     - Black-White KFR gap at P25.
   * - ``carceral_transition_modifier``
     - 2.8
     - Incarceration rate multiplier.
   * - ``early_mortality_modifier``
     - 1.24
     - Premature death multiplier.

**Chetty Table 8 Covariates**

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Parameter
     - Default
     - Description
   * - ``baseline_gini``
     - 0.485
     - National median Gini.
   * - ``poverty_share``
     - 0.126
     - National average poverty share.
   * - ``employment_rate``
     - 0.60
     - National average employment rate.
   * - ``single_parent_fraction``
     - 0.234
     - National average single-parent fraction.
   * - ``college_rate``
     - 0.33
     - National average college graduation rate.

**Ideology Transmission**

.. list-table::
   :header-rows: 1
   :widths: 40 10 50

   * - Parameter
     - Default
     - Description
   * - ``ideology_caregiver_weight``
     - 0.7
     - Caregiver influence in D-to-P transmission.
   * - ``ideology_institutional_weight``
     - 0.3
     - Institutional hegemony weight.
   * - ``ideology_regression_coefficient``
     - 0.4
     - Regression toward mean strength.

**Dual Circuit**

.. list-table::
   :header-rows: 1
   :widths: 40 10 50

   * - Parameter
     - Default
     - Description
   * - ``sandwich_squeeze_threshold``
     - 0.6
     - Dependency ratio triggering sandwich effect.

Module Structure
----------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Module
     - Contents
   * - :py:mod:`babylon.economics.lifecycle.types`
     - DPDState, LegitimationState, InheritanceFlow, ClassMobilityParams
   * - :py:mod:`babylon.economics.lifecycle.cohort_dynamics`
     - CohortDynamicsCalculator protocol + default implementation
   * - :py:mod:`babylon.economics.lifecycle.legitimation`
     - LegitimationCalculator protocol + default implementation
   * - :py:mod:`babylon.economics.lifecycle.inheritance`
     - InheritanceCalculator protocol + default implementation
   * - :py:mod:`babylon.economics.lifecycle.mobility`
     - ClassMobilityCalculator protocol + default implementation
   * - :py:mod:`babylon.economics.lifecycle.dual_circuit`
     - DualCircuitCalculator protocol + default implementation
   * - :py:mod:`babylon.formulas.lifecycle`
     - Six pure formula functions
   * - :py:mod:`babylon.engine.systems.lifecycle`
     - LifecycleSystem orchestrator

See Also
--------

- :doc:`/concepts/dpd-lifecycle-circuit` -- Theoretical foundations and dual circuit interference
- :doc:`/reference/community-system` -- Community hypergraph layer (lifecycle phases)
- :doc:`/reference/systems` -- System execution order
- :doc:`/reference/formulas` -- All simulation formulas
- :doc:`/reference/configuration` -- GameDefines parameter system
