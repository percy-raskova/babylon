"""Labor-side dynamics: reserve army, dispossession, working day.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.

**U8 defines sweep (vol1-value-production program, ADR114).** Every field
below now names its exact ``file:function`` consumer in its own
description, per the ADR116 ruling (b) house rule ("NO field lands
unread") — mirroring the ``capital_vol3.py`` -> ``CapitalVolumeIIIDefines``
citation convention (ADR089). Two findings from that sweep:

- ``ReserveArmyDefines.min_employed_fraction`` (Feature 021, FR-002) had
  zero consumers before this sweep (confirmed against
  ``specs/027-constants-provenance-audit/reports/constants-inventory.yaml``'s
  own ``consumers: []`` finding) — now wired as the reserve-ratio
  saturation floor in
  :meth:`~babylon.domain.economics.reserve_army.accumulation.DefaultAccumulationLoopCalculator.compute_reserve_ratio`
  (U8), mirroring ``wage_pressure_ceiling``'s "prevents total wage
  elimination" precedent on the labor-force side of the same mechanic.
- ``DispossessionDefines.weight_wage_theft`` /
  ``.weight_incarceration_seizure`` / ``.weight_pension_default`` (Feature
  021, FR-005) were REMOVED (U8): zero consumers, and — unlike
  ``weight_tax_sale``/``weight_eminent_domain``, which are genuinely read
  via the ``concentrated_ownership``/``absentee_landlord_share`` structural
  proxies :meth:`~babylon.domain.economics.dispossession.intensity.DispossessionIntensityCalculator.compute_intensity`
  already documents — no such proxy field exists on
  :class:`~babylon.domain.economics.dispossession.types.TerritoryDispossessionState`
  for wage theft, incarceration-related seizure, or pension default, and
  wiring one would require new data ingestion (out of program scope per
  the vol1-value-production program prompt §2h/§3: no drive-only data
  blocks this program, and new ingestion is a parquet-pipeline citizen
  gated on #46). Removing dead coefficients that can never be honestly
  fed is the Aleksandrov-Test-compliant choice over leaving fabricated
  config that silently does nothing (Constitution III.8/III.11). The
  ``DispossessionType`` enum's 8 categories are UNCHANGED — this only
  removes 3 dead AGGREGATE INTENSITY weights, not the per-event-type
  taxonomy FR-004 still records.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReserveArmyDefines(BaseModel):
    """Reserve army of labor coefficients (Feature 021, FR-001/FR-002/FR-003).

    Configures the bounded sigmoid that maps reserve_ratio to wage pressure
    (:mod:`babylon.domain.economics.reserve_army.calculator`) and the
    accumulation-loop flows that derive reserve_ratio itself in the first
    place (:mod:`babylon.domain.economics.reserve_army.accumulation`, Vol I
    U3, Ch. 25 — The General Law of Capitalist Accumulation). Higher reserve
    ratios produce stronger downward pressure on wages.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-001, FR-002, FR-003
    """

    model_config = ConfigDict(frozen=True)

    # Sigmoid parameters for wage pressure function
    sigmoid_k: float = Field(
        default=20.0,
        gt=0.0,
        le=100.0,
        description=(
            "Sigmoid steepness for reserve_ratio -> wage_pressure mapping. "
            "Consumer: "
            "babylon.domain.economics.reserve_army.calculator."
            "DefaultWagePressureCalculator.compute_wage_pressure."
        ),
    )
    sigmoid_r0: float = Field(
        default=0.08,
        gt=0.0,
        le=1.0,
        description=(
            "Reserve ratio at sigmoid midpoint (inflection point). "
            "Consumer: "
            "babylon.domain.economics.reserve_army.calculator."
            "DefaultWagePressureCalculator.compute_wage_pressure."
        ),
    )

    # Saturation ceiling for wage pressure
    wage_pressure_ceiling: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "Maximum wage pressure coefficient (prevents total wage "
            "elimination). Consumer: "
            "babylon.domain.economics.reserve_army.calculator."
            "DefaultWagePressureCalculator.compute_wage_pressure."
        ),
    )

    # Flow clamping
    min_employed_fraction: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum fraction of labor force that must remain employed — "
            "the reserve_ratio saturation floor (prevents total employment "
            "elimination, mirroring wage_pressure_ceiling's own precedent "
            "on the labor-force side of the same mechanic). Consumer "
            "(wired U8, vol1-value-production program defines sweep — zero "
            "consumers before this unit): "
            "babylon.domain.economics.reserve_army.accumulation."
            "DefaultAccumulationLoopCalculator.compute_reserve_ratio, which "
            "clamps reserve_ratio to [0, 1 - min_employed_fraction] rather "
            "than a bare [0, 1]."
        ),
    )

    # Accumulation loop (Capital Vol I U3, Ch. 25 — the General Law of
    # Capitalist Accumulation): parametrize
    # DefaultAccumulationLoopCalculator.compute_dynamics
    # (domain/economics/reserve_army/accumulation.py), which derives
    # ReserveArmyDynamics from organic-composition delta + FRED bankruptcy
    # rate, feeding a real reserve_ratio producer for ReserveArmySystem (#5).
    mechanization_displacement_rate: float = Field(
        default=0.05,
        gt=0.0,
        description=(
            "Game design: fraction of a county's employment displaced per "
            "1.0-unit year-over-year INCREASE in organic composition (c/v, "
            "from ValueTensor4x3.organic_composition) — parametrizes "
            "DefaultAccumulationLoopCalculator.compute_dynamics's "
            "mechanization_displacement flow. A falling or flat organic "
            "composition contributes zero displacement (Ch. 25 is about "
            "rising composition specifically). Consumer: "
            "babylon.domain.economics.reserve_army.accumulation."
            "DefaultAccumulationLoopCalculator.compute_dynamics."
        ),
    )
    firm_failure_conversion_rate: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description=(
            "Game design: fraction of a bankrupt establishment's workforce "
            "(FRED-derived bankruptcy_rate * employment) that enters the "
            "reserve army rather than being reabsorbed elsewhere — "
            "parametrizes DefaultAccumulationLoopCalculator.compute_dynamics's "
            "firm_failures flow. Consumer: "
            "babylon.domain.economics.reserve_army.accumulation."
            "DefaultAccumulationLoopCalculator.compute_dynamics."
        ),
    )


class DispossessionDefines(BaseModel):
    """Dispossession event intensity weights (Feature 021, FR-004/FR-005).

    Configures the relative weight of each TERRITORY-LEVEL-RATE dispossession
    type when computing aggregate territory-level dispossession intensity
    (:meth:`~babylon.domain.economics.dispossession.intensity.DispossessionIntensityCalculator.compute_intensity`).
    Five weights feed that computation directly or via a documented
    structural proxy; the ``DispossessionType`` enum's other three
    categories (wage theft, incarceration-related seizure, pension default)
    have no territory-level rate data source and carry no weight field here
    (U8 defines sweep removed the three dead placeholders — see the module
    docstring).

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-004, FR-005, FR-006
    """

    model_config = ConfigDict(frozen=True)

    # Intensity weights per dispossession type (must sum to ~1.0 over the
    # five territory-level-rate types the calculator actually reads)
    weight_foreclosure: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: weight for foreclosure events. Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_intensity "
            "(state.foreclosure_rate)."
        ),
    )
    weight_eviction: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: weight for eviction events. Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_intensity "
            "(state.eviction_rate)."
        ),
    )
    weight_displacement: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: weight for gentrification displacement events. "
            "Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_intensity "
            "(state.displacement_rate)."
        ),
    )
    weight_tax_sale: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: weight for tax sale events, read against the "
            "concentrated_ownership structural proxy (no direct tax-sale-"
            "rate field exists). Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_intensity "
            "(state.concentrated_ownership)."
        ),
    )
    weight_eminent_domain: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: weight for eminent domain events, read against "
            "the absentee_landlord_share structural proxy (no direct "
            "eminent-domain-rate field exists). Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_intensity "
            "(state.absentee_landlord_share)."
        ),
    )

    # Deadweight loss fraction for value transfers
    deadweight_loss_fraction: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: fraction of transferred value lost as deadweight "
            "(not received by anyone). Consumer: "
            "babylon.domain.economics.dispossession.intensity."
            "DispossessionIntensityCalculator.compute_value_transfer."
        ),
    )
    transfer_scale: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description=(
            "Scale factor for wealth transfer amount: territory_wealth * "
            "intensity * scale. Consumer: "
            "babylon.engine.systems.dispossession_events."
            "DispossessionEventSystem.step."
        ),
    )


class WorkingDayDefines(BaseModel):
    """Working day characterization thresholds (Feature 021, FR-007/FR-008/FR-011).

    Configures the threshold values for classifying territory-sector pairs
    by their dominant mode of surplus value extraction
    (:class:`~babylon.domain.economics.working_day.classifier.DefaultWorkingDayClassifier`),
    consumed by ``ConsciousnessSystem`` (Vol I U4, Ch. 10 — The Working Day)
    and the ``absolute_relative_surplus`` opposition (Vol I U6, Chs. 10, 12,
    15) via :mod:`babylon.domain.economics.working_day.resolver`.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-007, FR-008, FR-011
    """

    model_config = ConfigDict(frozen=True)

    # Hours thresholds for exploitation mode classification
    absolute_hours_threshold: float = Field(
        default=45.0,
        gt=0.0,
        le=168.0,
        description=(
            "Game design: weekly hours above which exploitation is "
            "ABSOLUTE_DOMINANT. Consumer: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.classify (also the upper bound of "
            "the MIXED-mode interpolation span in "
            "compute_visibility_modifier)."
        ),
    )
    relative_hours_threshold: float = Field(
        default=40.0,
        gt=0.0,
        le=168.0,
        description=(
            "Game design: weekly hours at or below which exploitation may "
            "be RELATIVE_DOMINANT. Consumers: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.classify/compute_visibility_modifier; "
            "and (Vol I U6) "
            "babylon.domain.economics.working_day.resolver."
            "resolve_absolute_relative_surplus_ratio, which reuses this "
            "same threshold as the ``absolute_relative_surplus`` "
            "opposition's hours reference — no second coefficient authored."
        ),
    )

    # Intensity thresholds for exploitation mode classification
    intensity_threshold_high: float = Field(
        default=1.2,
        gt=0.0,
        description=(
            "Game design: labor intensity above which exploitation is "
            "RELATIVE_DOMINANT (with low hours). Consumer: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.classify."
        ),
    )
    intensity_threshold_low: float = Field(
        default=1.1,
        gt=0.0,
        description=(
            "Game design: labor intensity below which exploitation is "
            "ABSOLUTE_DOMINANT (with high hours). Consumer: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.classify."
        ),
    )

    # Visibility modifiers for consciousness dynamics
    absolute_visibility: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: consciousness visibility modifier for ABSOLUTE "
            "exploitation. Consumer: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.compute_visibility_modifier, threaded "
            "into babylon.engine.systems.ideology.ConsciousnessSystem.step "
            "(Vol I U4) via "
            "babylon.formulas.consciousness_routing.compute_exploitation_visibility's "
            "working_day_modifier keyword."
        ),
    )
    relative_visibility: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: consciousness visibility modifier for RELATIVE "
            "exploitation. Consumer: "
            "babylon.domain.economics.working_day.classifier."
            "DefaultWorkingDayClassifier.compute_visibility_modifier, threaded "
            "into babylon.engine.systems.ideology.ConsciousnessSystem.step "
            "(Vol I U4) via "
            "babylon.formulas.consciousness_routing.compute_exploitation_visibility's "
            "working_day_modifier keyword."
        ),
    )


__all__ = [
    "DispossessionDefines",
    "ReserveArmyDefines",
    "WorkingDayDefines",
]
