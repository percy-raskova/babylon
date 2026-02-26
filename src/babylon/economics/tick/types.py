"""Type definitions for the Simulation Tick Dynamics pipeline.

Feature: 017-simulation-tick-dynamics, 018-crisis-devaluation-mechanics
Date: 2026-02-06

Frozen Pydantic models for the per-tick state evolution pipeline:
    - SimulationTickState: Root state container
    - NationalTickParameters: Year-scoped national economic context
    - CountyEconomicState: Per-county per-year economic snapshot
    - SmoothedCoefficients: Alpha-smoothed coefficient history
    - TickSummary: Aggregate statistics after tick completion
    - DerivedRates: Per-county derived economic indicators
    - CrisisPhase: 5-phase crisis lifecycle enum (Feature 018)
    - CrisisState: Per-county crisis status (Feature 018)
    - BifurcationRiskMetric: Political trajectory indicator (Feature 018)
    - PhasedAmplificationProfile: Phase-dependent multipliers (Feature 018)

See Also:
    :mod:`babylon.economics.dynamics.types`: ClassDistribution, EconomicConditions
    :mod:`babylon.economics.melt.types`: ClassPosition, PrecarityStatus
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.economics.circulation.types import CirculationCrisisState
from babylon.economics.counter_tendencies.types import CounterTendencyStrength
from babylon.economics.credit.types import CreditState, FictitiousCapitalStock, InterestRateState
from babylon.economics.distribution.types import DebtAccumulation, SurplusValueDistribution
from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.financial_crisis.types import FinancialCrisisAssessment
from babylon.economics.monetary.types import MonetaryAdjustment
from babylon.economics.rent.types import HousingValueDecomposition, RentExtraction


class CrisisPhase(StrEnum):
    """Crisis lifecycle phases for multi-period crisis detection.

    Feature: 018-crisis-devaluation-mechanics (FR-003)

    Crisis progresses through 5 phases based on consecutive periods
    of profit rate decline below threshold:

    Values:
        NORMAL: No active crisis.
        ONSET: Period N (first detection).
        EARLY: Periods N+1 through N+4.
        DEEP: Period N+5 onward.
        RECOVERY: Profit rate above threshold for M consecutive periods.
    """

    NORMAL = "normal"
    ONSET = "onset"
    EARLY = "early"
    DEEP = "deep"
    RECOVERY = "recovery"


class PhasedAmplificationProfile(BaseModel):
    """Phase-dependent multipliers for class transition rates.

    Feature: 018-crisis-devaluation-mechanics (FR-006)

    Downward rates (dispossession, precaritization) are amplified during
    crisis. Upward rates (accumulation, stabilization) are dampened.

    Args:
        dispossession_multiplier: LA -> Proletariat rate multiplier.
        precaritization_multiplier: Proletariat -> Lumpen rate multiplier.
        accumulation_multiplier: Proletariat -> LA rate multiplier (dampened).
        stabilization_multiplier: Lumpen -> Proletariat rate multiplier (dampened).
    """

    model_config = ConfigDict(frozen=True)

    dispossession_multiplier: float = Field(
        ..., gt=0, description="LA -> Proletariat rate multiplier"
    )
    precaritization_multiplier: float = Field(
        ..., gt=0, description="Proletariat -> Lumpen rate multiplier"
    )
    accumulation_multiplier: float = Field(
        ..., gt=0, le=1, description="Proletariat -> LA rate multiplier (dampened)"
    )
    stabilization_multiplier: float = Field(
        ..., gt=0, le=1, description="Lumpen -> Proletariat rate multiplier (dampened)"
    )


class CrisisState(BaseModel):
    """Per-county crisis status tracking the full lifecycle.

    Feature: 018-crisis-devaluation-mechanics (FR-002, FR-003)

    Immutable state object updated each crisis evaluation period.
    Tracks phase, duration counters, and severity metrics.

    Args:
        phase: Current crisis lifecycle phase.
        consecutive_below: Periods consecutively below r_threshold.
        consecutive_recovery: Periods consecutively above r_threshold (during recovery).
        crisis_start_period: Period index when crisis was first detected (None if NORMAL).
        crisis_duration: Total periods in crisis (ONSET through DEEP).
        peak_severity: Lowest profit rate observed during this crisis (None if NORMAL).
        cumulative_wage_compression: Total wage compression applied [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    phase: CrisisPhase = Field(
        default=CrisisPhase.NORMAL, description="Current crisis lifecycle phase"
    )
    consecutive_below: int = Field(
        default=0, ge=0, description="Periods consecutively below r_threshold"
    )
    consecutive_recovery: int = Field(
        default=0, ge=0, description="Periods consecutively above r_threshold in recovery"
    )
    crisis_start_period: int | None = Field(
        default=None, description="Period when crisis first detected"
    )
    crisis_duration: int = Field(default=0, ge=0, description="Total periods in active crisis")
    peak_severity: float | None = Field(
        default=None, description="Lowest profit rate during this crisis"
    )
    cumulative_wage_compression: float = Field(
        default=0.0, ge=0, le=1, description="Total wage compression applied"
    )

    @classmethod
    def normal(cls) -> CrisisState:
        """Factory for a clean NORMAL state with all counters zeroed.

        Returns:
            CrisisState in NORMAL phase with all counters at zero.
        """
        return cls(
            phase=CrisisPhase.NORMAL,
            consecutive_below=0,
            consecutive_recovery=0,
            crisis_start_period=None,
            crisis_duration=0,
            peak_severity=None,
            cumulative_wage_compression=0.0,
        )


class BifurcationRiskMetric(BaseModel):
    """Political trajectory indicator during crisis.

    Feature: 018-crisis-devaluation-mechanics (FR-011)

    Synthesizes solidarity topology, legitimation, and class burden
    into a directional score [-1, +1] where -1 is revolutionary
    and +1 is fascist.

    Args:
        score: Composite bifurcation score [-1, +1].
        solidarity_density: Fraction of cross-class SOLIDARITY edges [0, 1].
        legitimation: Inverse of aggregate agitation [0, 1].
        class_burden_ratio: |delta_LA| / max(|delta_Prol|, epsilon) clamped [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    score: float = Field(default=0.0, ge=-1, le=1, description="Composite bifurcation score")
    solidarity_density: float = Field(
        default=0.0, ge=0, le=1, description="Cross-class SOLIDARITY edge fraction"
    )
    legitimation: float = Field(
        default=1.0, ge=0, le=1, description="Inverse of aggregate agitation"
    )
    class_burden_ratio: float = Field(
        default=0.0, ge=0, le=1, description="LA burden relative to proletariat"
    )

    @classmethod
    def neutral(cls) -> BifurcationRiskMetric:
        """Factory for a neutral metric (no crisis, no bifurcation risk).

        Returns:
            BifurcationRiskMetric with score=0, full legitimation.
        """
        return cls(
            score=0.0,
            solidarity_density=0.0,
            legitimation=1.0,
            class_burden_ratio=0.0,
        )


class NationalTickParameters(BaseModel):
    """Year-scoped national economic context computed once per tick.

    Extends Feature 013's NationalParameters with smoothed variants
    and gamma_III for the tick pipeline.

    Args:
        year: Parameter year.
        tau: National MELT ($/labor-hour).
        gamma_basket: Basket visibility (smoothed).
        gamma_basket_raw: Basket visibility (raw computed).
        gamma_III: Reproductive visibility (smoothed).
        gamma_III_raw: Reproductive visibility (raw computed).
        tau_effective: Effective MELT = tau x gamma_basket.
        v_reproduction: Subsistence cost ($/hour).
        estimated: True if using MVP hardcoded values.

    Example:
        >>> params = NationalTickParameters(
        ...     year=2015, tau=62.0,
        ...     gamma_basket=0.68, gamma_basket_raw=0.68,
        ...     gamma_III=0.33, gamma_III_raw=0.33,
        ...     tau_effective=42.16, v_reproduction=12.0,
        ...     estimated=True,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040, description="Parameter year")
    tau: float = Field(..., gt=0, description="National MELT ($/labor-hour)")
    gamma_basket: float = Field(..., gt=0, le=1, description="Basket visibility (smoothed)")
    gamma_basket_raw: float = Field(..., gt=0, le=1, description="Basket visibility (raw)")
    gamma_III: float = Field(..., gt=0, le=1, description="Reproductive visibility (smoothed)")
    gamma_III_raw: float = Field(..., gt=0, le=1, description="Reproductive visibility (raw)")
    tau_effective: float = Field(..., gt=0, description="Effective MELT = tau x gamma_basket")
    v_reproduction: float = Field(..., gt=0, description="Subsistence cost ($/hour)")
    estimated: bool = Field(default=False, description="True if using MVP hardcoded values")


class DerivedRates(BaseModel):
    """Per-county derived economic indicators computed from updated state.

    Division-by-zero yields None (mathematically undefined), which is
    distinct from NoDataSentinel (data unavailability during init).

    Args:
        fips: County FIPS code.
        year: Rate year.
        profit_rate: r = s / (K + v), None if division by zero.
        organic_composition: OCC = c / v, None if v=0.
        exploitation_rate: e = s / v, None if v=0.
        phi_hour: Imperial rent per labor-hour.

    Example:
        >>> rates = DerivedRates(
        ...     fips="26163", year=2015,
        ...     profit_rate=0.15, organic_composition=3.2,
        ...     exploitation_rate=1.5, phi_hour=3.50,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2040, description="Rate year")
    profit_rate: float | None = Field(default=None, description="r = s/(K+v), None if undefined")
    organic_composition: float | None = Field(
        default=None, ge=0, description="OCC = c/v, None if v=0"
    )
    exploitation_rate: float | None = Field(default=None, ge=0, description="e = s/v, None if v=0")
    phi_hour: float = Field(..., ge=0, description="Imperial rent per labor-hour")


class CountyEconomicState(BaseModel):
    """Per-county per-year economic snapshot.

    During initialization, fields are seeded from census data.
    During simulation ticks, fields are computed by the engine.

    Args:
        fips: County FIPS code.
        year: State year.
        capital_stock: Capital stock K (Feature 012).
        throughput_position: Pi = tau_through / tau_national (Feature 014).
        supply_chain_depth: Average supply chain depth D.
        unemployment_rate: County unemployment (U-3 proxy).
        u6_rate: Broad unemployment (U-6).
        pter_rate: Part-time for economic reasons.
        nilf_rate: Not in labor force rate.
        median_wage: County median hourly wage.
        employment: Total county employment.
        class_distribution: Five-class share distribution.
        phi_hour: Imperial rent per hour (Feature 013).
        crisis_state: Crisis lifecycle state (Feature 018).
        bifurcation_risk: Political trajectory indicator (Feature 018).

    Example:
        >>> state = CountyEconomicState(
        ...     fips="26163", year=2015,
        ...     capital_stock=1e9, throughput_position=0.9,
        ...     supply_chain_depth=2.1,
        ...     unemployment_rate=0.053, u6_rate=0.10,
        ...     pter_rate=0.04, nilf_rate=0.06,
        ...     median_wage=21.0, employment=500000.0,
        ...     class_distribution=dist, phi_hour=3.50,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2040, description="State year")
    capital_stock: float = Field(..., ge=0, description="Capital stock K")
    throughput_position: float = Field(..., gt=0, description="Pi = tau_through / tau_national")
    supply_chain_depth: float = Field(..., ge=0, le=5, description="Supply chain depth D")
    unemployment_rate: float = Field(..., ge=0, le=1, description="County unemployment (U-3)")
    u6_rate: float = Field(..., ge=0, le=1, description="Broad unemployment (U-6)")
    pter_rate: float = Field(..., ge=0, le=1, description="Part-time for economic reasons")
    nilf_rate: float = Field(..., ge=0, le=1, description="Not in labor force rate")
    median_wage: float = Field(..., ge=0, description="County median hourly wage")
    employment: float = Field(..., ge=0, description="Total county employment")
    class_distribution: ClassDistribution = Field(..., description="Five-class share distribution")
    phi_hour: float = Field(..., ge=0, description="Imperial rent per hour")
    crisis_state: CrisisState = Field(
        default_factory=CrisisState.normal,
        description="Crisis lifecycle state for this county-year (Feature 018)",
    )
    bifurcation_risk: BifurcationRiskMetric = Field(
        default_factory=BifurcationRiskMetric.neutral,
        description="Political trajectory indicator (Feature 018)",
    )
    circulation_state: CirculationCrisisState = Field(
        default_factory=CirculationCrisisState.default,
        description="Capital circulation state (Feature 023)",
    )
    # Financial distribution state (Feature 024)
    surplus_distribution: SurplusValueDistribution | None = Field(
        default=None,
        description="Surplus value distribution (Feature 024)",
    )
    rent_extraction: RentExtraction | None = Field(
        default=None,
        description="Ground rent by category (Feature 024)",
    )
    housing_decomposition: HousingValueDecomposition | None = Field(
        default=None,
        description="Housing value decomposition (Feature 024)",
    )
    debt_accumulation: DebtAccumulation | None = Field(
        default=None,
        description="Cumulative debt tracker (Feature 024)",
    )
    financial_crisis: FinancialCrisisAssessment | None = Field(
        default=None,
        description="Integrated financial crisis assessment (Feature 024)",
    )


class SmoothedCoefficients(BaseModel):
    """Container for alpha-smoothed coefficients that persist across ticks.

    Update rule: value[t] = value[t-1] + alpha * (raw[t] - value[t-1])
    First tick: value[0] = raw[0] (no smoothing applied).

    Args:
        alpha: Smoothing parameter (0, 1].
        gamma_basket: Current smoothed basket visibility.
        gamma_III: Current smoothed reproductive visibility.
        gamma_import: Current smoothed import visibility.
        is_initialized: False until first tick completes.

    Example:
        >>> coeff = SmoothedCoefficients(
        ...     alpha=0.3, gamma_basket=0.68,
        ...     gamma_III=0.33, gamma_import=0.35,
        ...     is_initialized=True,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    alpha: float = Field(..., gt=0, le=1, description="Smoothing parameter")
    gamma_basket: float = Field(..., gt=0, le=1, description="Smoothed basket visibility")
    gamma_III: float = Field(..., gt=0, le=1, description="Smoothed reproductive visibility")
    gamma_import: float = Field(..., gt=0, le=1, description="Smoothed import visibility")
    is_initialized: bool = Field(default=False, description="False until first tick completes")


class TickSummary(BaseModel):
    """Aggregate statistics for a completed tick.

    Args:
        year: Tick year.
        counties_processed: Number of counties computed.
        phi_aggregate: Total national imperial rent.
        national_melt: National MELT (tau).
        mean_profit_rate: Average profit rate across counties.
        mean_occ: Average organic composition.
        mean_exploitation_rate: Average exploitation rate.
        national_class_distribution: Weighted-average class shares.

    Example:
        >>> summary = TickSummary(
        ...     year=2015, counties_processed=3,
        ...     phi_aggregate=1e12, national_melt=62.0,
        ...     mean_profit_rate=0.15, mean_occ=3.2,
        ...     mean_exploitation_rate=1.5,
        ...     national_class_distribution={
        ...         "bourgeoisie": 0.01, "petit_bourgeoisie": 0.09,
        ...         "labor_aristocracy": 0.40, "proletariat": 0.35,
        ...         "lumpenproletariat": 0.15,
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040, description="Tick year")
    counties_processed: int = Field(..., ge=0, description="Number of counties computed")
    phi_aggregate: float = Field(..., ge=0, description="Total national imperial rent")
    national_melt: float = Field(..., gt=0, description="National MELT (tau)")
    mean_profit_rate: float = Field(..., description="Average profit rate")
    mean_occ: float = Field(..., ge=0, description="Average organic composition")
    mean_exploitation_rate: float = Field(..., ge=0, description="Average exploitation rate")
    national_class_distribution: dict[str, float] = Field(
        ..., description="Weighted-average class shares"
    )


class NationalFinancialParameters(BaseModel):
    """National-level financial state computed once per tick.

    Feature: 024-capital-volume-iii

    Contains interest rates, credit state, fictitious capital,
    counter-tendencies, and monetary adjustment factors.

    Args:
        interest_rate_state: National interest rate environment.
        credit_state: Credit system health.
        fictitious_capital: Accumulated financial claims.
        counter_tendencies: TRPF counter-tendency indicators.
        monetary_adjustment: Value basis conversion factors.
    """

    model_config = ConfigDict(frozen=True)

    interest_rate_state: InterestRateState | None = Field(
        default=None, description="National interest rate environment"
    )
    credit_state: CreditState | None = Field(default=None, description="Credit system health")
    fictitious_capital: FictitiousCapitalStock | None = Field(
        default=None, description="Accumulated financial claims"
    )
    counter_tendencies: CounterTendencyStrength | None = Field(
        default=None, description="TRPF counter-tendency indicators"
    )
    monetary_adjustment: MonetaryAdjustment | None = Field(
        default=None, description="Value basis conversion factors"
    )

    @classmethod
    def empty(cls) -> NationalFinancialParameters:
        """Factory for initial state with no financial data.

        Returns:
            NationalFinancialParameters with all fields set to None.
        """
        return cls()


class SimulationTickState(BaseModel):
    """Complete simulation state at a point in time.

    Pure data container, immutable. Serves as both output of tick t
    and input to tick t+1.

    Args:
        year: Current simulation year.
        national_params: Year-scoped national context.
        county_states: Per-county snapshots keyed by FIPS.
        coefficients: Alpha-smoothed coefficient history.
        tick_summary: Aggregate stats (populated after tick completes).

    Example:
        >>> state = SimulationTickState(
        ...     year=2015,
        ...     national_params=params,
        ...     county_states={"26163": wayne_state},
        ...     coefficients=coeff,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040, description="Current simulation year")
    national_params: NationalTickParameters = Field(..., description="National context")
    county_states: dict[str, CountyEconomicState] = Field(
        ..., description="Per-county snapshots keyed by FIPS"
    )
    coefficients: SmoothedCoefficients = Field(..., description="Alpha-smoothed coefficients")
    tick_summary: TickSummary | None = Field(
        default=None, description="Aggregate stats (populated after tick completes)"
    )

    @model_validator(mode="after")
    def _validate_fips_keys(self) -> SimulationTickState:
        """Ensure county_states keys match their CountyEconomicState.fips values."""
        max_counties = 3300  # US has ~3,143 counties; allow headroom
        if len(self.county_states) > max_counties:
            msg = f"Too many counties: {len(self.county_states)} > {max_counties}"
            raise ValueError(msg)
        for key, county in self.county_states.items():
            if key != county.fips:
                msg = f"Key {key!r} does not match county FIPS {county.fips!r}"
                raise ValueError(msg)
        return self


__all__ = [
    "BifurcationRiskMetric",
    "CountyEconomicState",
    "CrisisPhase",
    "CrisisState",
    "DerivedRates",
    "NationalFinancialParameters",
    "NationalTickParameters",
    "PhasedAmplificationProfile",
    "SimulationTickState",
    "SmoothedCoefficients",
    "TickSummary",
]
