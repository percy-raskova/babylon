"""Type definitions for the Simulation Tick Dynamics pipeline.

Feature: 017-simulation-tick-dynamics
Date: 2026-02-06

Frozen Pydantic models for the per-tick state evolution pipeline:
    - SimulationTickState: Root state container
    - NationalTickParameters: Year-scoped national economic context
    - CountyEconomicState: Per-county per-year economic snapshot
    - SmoothedCoefficients: Alpha-smoothed coefficient history
    - TickSummary: Aggregate statistics after tick completion
    - DerivedRates: Per-county derived economic indicators

See Also:
    :mod:`babylon.economics.dynamics.types`: ClassDistribution, EconomicConditions
    :mod:`babylon.economics.melt.types`: ClassPosition, PrecarityStatus
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.economics.dynamics.types import ClassDistribution


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
        crisis: Crisis flag for this county-year.

    Example:
        >>> state = CountyEconomicState(
        ...     fips="26163", year=2015,
        ...     capital_stock=1e9, throughput_position=0.9,
        ...     supply_chain_depth=2.1,
        ...     unemployment_rate=0.053, u6_rate=0.10,
        ...     pter_rate=0.04, nilf_rate=0.06,
        ...     median_wage=21.0, employment=500000.0,
        ...     class_distribution=dist, phi_hour=3.50,
        ...     crisis=False,
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
    crisis: bool = Field(default=False, description="Crisis flag for this county-year")


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
    "CountyEconomicState",
    "DerivedRates",
    "NationalTickParameters",
    "SimulationTickState",
    "SmoothedCoefficients",
    "TickSummary",
]
