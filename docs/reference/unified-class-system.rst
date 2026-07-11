Unified Class System Reference
===============================

API reference for the unified class system (Feature 038). Covers
configuration, filtration predicates, the unified classifier protocol,
rent differential calculation, class-aware inheritance, crisis
dispossession, and fractal consistency validation.

.. contents:: On this page
   :local:
   :depth: 2

ClassSystemDefines
------------------

Centralized coefficients for the unified class system. Sub-model of
``GameDefines``, accessed via ``GameDefines().class_system``.

Defined in :py:class:`~babylon.config.defines.ClassSystemDefines`.

.. list-table::
   :header-rows: 1
   :widths: 30 10 10 50

   * - Field
     - Type
     - Default
     - Description
   * - ``trust_land_discount``
     - float
     - 0.5
     - Fed SCF / BIA discount on effective wealth for FIRST_NATIONS
       trust land property. 0.5 = 50% reduction. [0, 1]
   * - ``documentation_exclusion_factor``
     - float
     - 0.6
     - Discount on effective wealth for UNDOCUMENTED households.
       0.6 = 40% reduction. [0, 1]
   * - ``equity_factor``
     - float
     - 0.6
     - Fraction of homeowners with meaningful equity. Calibrated:
       65% ownership * 0.6 = 39% ~ 40% LA share. [0, 1]
   * - ``base_class_solidarity``
     - dict
     - *(matrix)*
     - Symmetric 5x5 class-pair base solidarity matrix.
       15 unique values (upper triangle including diagonal). All values
       in [0, 1].

**Solidarity Matrix Defaults:**

.. list-table::
   :header-rows: 1
   :widths: 22 16 16 16 16 16

   * - From \\ To
     - BOURG
     - PB
     - LA
     - PROL
     - LUMPEN
   * - BOURGEOISIE
     - 0.70
     - 0.30
     - 0.10
     - 0.00
     - 0.00
   * - PETIT_BOURGEOISIE
     - 0.30
     - 0.50
     - 0.40
     - 0.15
     - 0.05
   * - LABOR_ARISTOCRACY
     - 0.10
     - 0.40
     - 0.60
     - 0.30
     - 0.10
   * - PROLETARIAT
     - 0.00
     - 0.15
     - 0.30
     - 0.80
     - 0.50
   * - LUMPENPROLETARIAT
     - 0.00
     - 0.05
     - 0.10
     - 0.50
     - 0.60

**Methods:**

.. code-block:: text

   def get_base_solidarity(self, class_a: str, class_b: str) -> float

Symmetric lookup into the matrix. Returns 0.0 for unknown pairs.

Filtration Predicates
---------------------

Community-specific filtration predicates modify classification inputs
based on hyperedge memberships (FR-003, FR-004).

Defined in :py:mod:`babylon.domain.economics.melt.filtration`.

FiltrationResult
~~~~~~~~~~~~~~~~

Frozen Pydantic model returned by ``apply_filtration()``.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Field
     - Type
     - Default
     - Description
   * - ``original_wealth_percentile``
     - float
     - *required*
     - Input wealth percentile before filtration. [0, 100]
   * - ``effective_wealth_percentile``
     - float
     - *required*
     - Wealth percentile after filtration. [0, 100]
   * - ``original_precarity``
     - PrecarityStatus
     - *required*
     - Input precarity before filtration
   * - ``effective_precarity``
     - PrecarityStatus
     - *required*
     - Precarity after filtration
   * - ``applied_predicates``
     - list[str]
     - []
     - Names of predicates that fired
   * - ``most_restrictive_community``
     - CommunityType | None
     - None
     - Community that produced the most restrictive result

**Validators:** ``effective_wealth_percentile <= original_wealth_percentile``.
``effective_precarity`` severity >= ``original_precarity`` severity.

apply_filtration
~~~~~~~~~~~~~~~~

.. code-block:: text

   def apply_filtration(
       wealth_percentile: float,
       precarity: PrecarityStatus,
       memberships: list[CommunityMembership],
       community_states: dict[str, CommunityState],
       defines: ClassSystemDefines | None = None,
   ) -> FiltrationResult

Evaluates each predicate independently against original inputs. The
most restrictive composite result (lowest wealth, highest precarity
severity) is used.

**Per-predicate formulas:**

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Community
     - Wealth Effect
     - Precarity Effect
   * - FIRST_NATIONS
     - ``wealth * trust_land_discount``
     - unchanged
   * - INCARCERATED
     - unchanged
     - override to EXCLUDED
   * - UNDOCUMENTED
     - ``wealth * documentation_exclusion_factor``
     - floor at PRECARIOUS
   * - DISABLED
     - ``wealth / reproduction_cost_modifier``
     - unchanged

**Precarity severity ordering:** STABLE (0) < PRECARIOUS (1) <
MARGINALLY_ATTACHED (2) < EXCLUDED (3).

**Composition (FR-004):** Multiple predicates evaluate independently;
most-restrictive-wins for both wealth and precarity. Result is
order-independent.

UnifiedClassifier Protocol
--------------------------

Protocol for unified class position classification. Wraps the
existing ``DefaultClassPositionClassifier`` with filtration and
dual-criteria validation.

Defined in :py:mod:`babylon.domain.economics.melt.unified_classifier`.

classify_with_filtration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def classify_with_filtration(
       self,
       wealth_percentile: float,
       precarity: PrecarityStatus,
       memberships: list[CommunityMembership] | None = None,
       community_states: dict[str, CommunityState] | None = None,
   ) -> ClassPosition

Applies filtration predicates to inputs, then delegates to the base
wealth-percentile classifier. Without memberships, behaves identically
to the existing classifier.

classify_dual_criteria
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def classify_dual_criteria(
       self,
       wealth_percentile: float,
       precarity: PrecarityStatus,
       v_produced: float,
       v_reproduction: float,
       memberships: list[CommunityMembership] | None = None,
       community_states: dict[str, CommunityState] | None = None,
   ) -> DualCriteriaResult

Compares wealth-percentile classification against accounting criterion.
Returns agreement status and disagreement magnitude for calibration.

DualCriteriaResult
~~~~~~~~~~~~~~~~~~

Frozen Pydantic model for dual-criteria validation output.

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``wealth_class``
     - ClassPosition
     - ClassPosition from wealth percentile criterion
   * - ``accounting_class``
     - ClassPosition
     - ClassPosition from accounting criterion
   * - ``agrees``
     - bool
     - True if both criteria produce the same ClassPosition
   * - ``magnitude``
     - float
     - Disagreement magnitude (0.0 when agrees is True). >= 0.0

**Validators:** ``agrees`` must be consistent with ``wealth_class ==
accounting_class``. ``magnitude`` must be 0.0 when ``agrees`` is True.

Accounting Criterion
--------------------

Maps the ratio :math:`R = V_{\text{produced}} / V_{\text{reproduction}}`
to ``ClassPosition``.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Ratio Range
     - ClassPosition
     - Interpretation
   * - :math:`R \geq 1.5`
     - BOURGEOISIE
     - Surplus extraction
   * - :math:`1.2 \leq R < 1.5`
     - PETIT_BOURGEOISIE
     - Simple reproduction with buffer
   * - :math:`0.8 \leq R < 1.2`
     - PROLETARIAT
     - Simple reproduction
   * - :math:`0.5 \leq R < 0.8`
     - PROLETARIAT
     - Below reproduction
   * - :math:`R < 0.5`
     - LUMPENPROLETARIAT
     - Dependent

When :math:`V_{\text{reproduction}} \leq 0`, returns BOURGEOISIE
(living off capital, no reproduction cost).

Module-level constants: ``_SURPLUS_THRESHOLD = 1.5``,
``_SIMPLE_REPRO_UPPER = 1.2``, ``_SIMPLE_REPRO_LOWER = 0.8``,
``_DEPENDENT_THRESHOLD = 0.5``.

Defined in ``_accounting_criterion()`` within
:py:mod:`babylon.domain.economics.melt.unified_classifier`.

Fractal Consistency
-------------------

Validates that classification produces coherent results across
geographic resolutions (FR-009).

Defined in :py:mod:`babylon.domain.economics.melt.unified_classifier`.

validate_fractal_consistency
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def validate_fractal_consistency(
       county_distributions: dict[str, dict[ClassPosition, float]],
   ) -> FractalConsistencyResult

Checks that each county has all five class positions represented and
that distributions sum to approximately 1.0. Computes metro-level
aggregate as equal-weighted average across counties.

FractalConsistencyResult
~~~~~~~~~~~~~~~~~~~~~~~~

Frozen Pydantic model.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Field
     - Type
     - Description
   * - ``is_consistent``
     - bool
     - True if fractal pattern holds across all counties
   * - ``proletariat_lumpen_share``
     - dict[str, float]
     - PROLETARIAT + LUMPEN share per county FIPS
   * - ``class_positions_present``
     - dict[str, set[ClassPosition]]
     - Set of ClassPositions present per county FIPS
   * - ``metro_distribution``
     - dict[ClassPosition, float]
     - Population-weighted metro-level distribution

Rent Differential Calculator
-----------------------------

Protocol for computing nation-specific imperial rent differentials
from ACS earnings data by race x NAICS at county level (FR-007).

Defined in :py:mod:`babylon.domain.economics.melt.rent_differential`.

RentDifferentialCalculator Protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   class RentDifferentialCalculator(Protocol):

       def compute_differential(
           self,
           fips: str,
           nation: CommunityType,
           naics: str,
           year: int,
       ) -> float | NoDataSentinel: ...

       def compute_county_aggregate(
           self,
           fips: str,
           nation: CommunityType,
           year: int,
       ) -> float | NoDataSentinel: ...

``compute_differential()`` returns :math:`\Phi_{\text{diff}} =
W_{\text{settler}} - W_{\text{nation}}` for a specific
county x nation x NAICS combination. Positive values indicate settler
advantage. SETTLER self-differential returns 0.0.

``compute_county_aggregate()`` returns the employment-weighted average
differential across all NAICS codes for a county-nation pair. QCEW
employment counts provide the weights.

**NoDataSentinel propagation:** Suppressed ACS data (missing county,
NAICS, or nation earnings) returns ``NoDataSentinel`` rather than
imputing values. See :py:class:`~babylon.domain.economics.tensor.NoDataSentinel`.

RentDifferentialResult
~~~~~~~~~~~~~~~~~~~~~~

Frozen Pydantic model for aggregate results.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``fips``
     - str
     - 5-digit FIPS code (length 5)
   * - ``nation``
     - CommunityType
     - Target nation
   * - ``year``
     - int
     - Calendar year [2000, 2100]
   * - ``differential``
     - float
     - Employment-weighted average differential ($/year)
   * - ``naics_count``
     - int
     - Number of NAICS codes with valid data (>= 0)
   * - ``suppressed_count``
     - int
     - Number of NAICS codes with suppressed data (>= 0)

**Validators:** ``naics_count + suppressed_count > 0``.

Class-Aware Inheritance
-----------------------

Extension to the existing ``InheritanceCalculator`` protocol
(Feature 030) that scales inheritance by class position.

Defined in :py:mod:`babylon.domain.economics.lifecycle.inheritance`.

compute_class_aware_inheritance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def compute_class_aware_inheritance(
       self,
       dpd_state: DPDState,
       class_position: ClassPosition,
       pareto_alpha: float,
       care_cost_fraction: float,
       *,
       foreclosed: bool = False,
   ) -> InheritanceFlow | None

Computes inheritance flow scaled by class position. Returns ``None``
if no D' deaths occurred in this tick.

**Class inheritance scale factors:**

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - ClassPosition
     - Scale
     - Rationale
   * - BOURGEOISIE
     - 1.0
     - Full estate transfer
   * - PETIT_BOURGEOISIE
     - 0.7
     - Business capital transfer
   * - LABOR_ARISTOCRACY
     - 0.5
     - Home equity (primary vehicle)
   * - PROLETARIAT
     - 0.05
     - Minimal (consumed by reproduction)
   * - LUMPENPROLETARIAT
     - 0.0
     - No inheritable wealth

**Foreclosure behavior:** When ``foreclosed=True``, net inheritance is
zero regardless of class position. ``care_consumed`` absorbs the full
``total_transferred`` amount. The inheritance mechanism is severed.

Crisis Dispossession
--------------------

Models crisis-driven wealth destruction events (foreclosure, eviction)
with community-modifiable targeting (FR-010).

Defined in :py:mod:`babylon.domain.economics.lifecycle.dispossession`.

compute_crisis_dispossession
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   def compute_crisis_dispossession(
       household_wealth: float,
       foreclosure_rate: float,
       community_targeting_multiplier: float = 1.0,
   ) -> DispossessionResult

Computes wealth destruction from a crisis event.

**Formulas:**

.. math::

   r_{\text{eff}} = \min(1.0, \; r_{\text{base}} \times m_{\text{target}})

.. math::

   W_{\text{destroyed}} = W \times r_{\text{eff}}

.. math::

   W_{\text{remaining}} = W - W_{\text{destroyed}}

Class position change is indicated when :math:`W_{\text{remaining}} <
0.5 \times W` (household lost more than half its wealth).

DispossessionResult
~~~~~~~~~~~~~~~~~~~

Frozen Pydantic model.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Type
     - Description
   * - ``household_wealth``
     - float
     - Original household wealth (>= 0)
   * - ``foreclosure_rate``
     - float
     - Base foreclosure rate [0, 1]
   * - ``effective_rate``
     - float
     - Actual rate after targeting multiplier [0, 1]
   * - ``wealth_destroyed``
     - float
     - Amount destroyed by crisis (>= 0)
   * - ``remaining_wealth``
     - float
     - Wealth after dispossession (>= 0)
   * - ``class_position_change_indicated``
     - bool
     - True if remaining < 50% of original

**Validators:** ``wealth_destroyed + remaining_wealth ==
household_wealth`` (tolerance 0.01). Wealth conservation invariant.

Module Structure
----------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Module
     - Public Exports
   * - ``babylon.domain.economics.melt.filtration``
     - ``FiltrationResult``, ``apply_filtration``, ``precarity_severity``
   * - ``babylon.domain.economics.melt.unified_classifier``
     - ``DefaultUnifiedClassifier``, ``DualCriteriaResult``,
       ``FractalConsistencyResult``, ``UnifiedClassifier``,
       ``validate_fractal_consistency``
   * - ``babylon.domain.economics.melt.rent_differential``
     - ``DefaultRentDifferentialCalculator``,
       ``RentDifferentialCalculator``, ``RentDifferentialResult``
   * - ``babylon.domain.economics.lifecycle.inheritance``
     - ``DefaultInheritanceCalculator``, ``InheritanceCalculator``
   * - ``babylon.domain.economics.lifecycle.dispossession``
     - ``DispossessionResult``, ``compute_crisis_dispossession``
   * - ``babylon.config.defines``
     - ``ClassSystemDefines`` (sub-model of ``GameDefines``)

See Also
--------

- :doc:`/concepts/unified-class-system` --- Theoretical foundations
  and rationale
- :doc:`/reference/community-system` --- Solidarity potential formula
  and community system API
- :doc:`/reference/lifecycle-system` --- D-P-D' lifecycle reference
- :doc:`/reference/economics-pipeline` --- Economics pipeline data
  types and formulas
- :doc:`/reference/configuration` --- GameDefines parameter tables
