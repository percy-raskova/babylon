"""Type definitions for the Class Dynamics Engine.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

This module defines frozen Pydantic models for class distribution state,
economic conditions, transition rates, and supporting types.

Models:
    - ClassDistribution: Five-class share distribution (sum-to-one invariant)
    - EconomicConditions: County-year economic state inputs
    - TransitionRates: Four-pathway transition rate structure
    - AccumulationResult: Wealth accumulation computation output
    - DispossessionRisk: Composite dispossession risk assessment
    - SavingsRateSchedule: Class-based savings rate lookup

See Also:
    :mod:`babylon.domain.economics.melt.types`: ClassPosition enum (Feature 013)
    :mod:`babylon.domain.economics.dynamics.validation`: Three-tier validation
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClassDistribution(BaseModel):
    """Five-class share distribution for a county-year.

    The primary state object of the dynamics engine. All five shares must
    sum to 1.0 within tolerance. Bourgeoisie and petit-bourgeoisie shares
    are externally determined; the engine operates on LA/proletariat/lumpen.

    Args:
        fips: County FIPS code (5 characters).
        year: Calendar year.
        bourgeoisie_share: Top 1% wealth share.
        petit_bourgeoisie_share: 90th-99th percentile share.
        labor_aristocracy_share: 50th-90th percentile share.
        proletariat_share: Bottom 50% employed share.
        lumpenproletariat_share: Bottom 50% excluded share.

    Example:
        >>> dist = ClassDistribution(
        ...     fips="26163", year=2015,
        ...     bourgeoisie_share=0.01, petit_bourgeoisie_share=0.09,
        ...     labor_aristocracy_share=0.40, proletariat_share=0.35,
        ...     lumpenproletariat_share=0.15,
        ... )
        >>> dist.dynamic_shares()
        (0.4, 0.35, 0.15)
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2030, description="Calendar year")
    bourgeoisie_share: float = Field(..., ge=0.0, le=1.0, description="Top 1% wealth share")
    petit_bourgeoisie_share: float = Field(
        ..., ge=0.0, le=1.0, description="90th-99th percentile share"
    )
    labor_aristocracy_share: float = Field(
        ..., ge=0.0, le=1.0, description="50th-90th percentile share"
    )
    proletariat_share: float = Field(..., ge=0.0, le=1.0, description="Bottom 50% employed share")
    lumpenproletariat_share: float = Field(
        ..., ge=0.0, le=1.0, description="Bottom 50% excluded share"
    )

    @model_validator(mode="after")
    def _validate_sum_to_one(self) -> ClassDistribution:
        """Enforce sum-to-one invariant (tolerance 0.001)."""
        total = (
            self.bourgeoisie_share
            + self.petit_bourgeoisie_share
            + self.labor_aristocracy_share
            + self.proletariat_share
            + self.lumpenproletariat_share
        )
        if abs(total - 1.0) > 0.001:
            msg = f"Class shares must sum to 1.0 (within 0.001 tolerance), got {total:.6f}"
            raise ValueError(msg)
        return self

    def total_share_check(self) -> bool:
        """Check if shares sum to 1.0 within tolerance.

        Returns:
            True if sum is within 0.001 of 1.0.
        """
        total = (
            self.bourgeoisie_share
            + self.petit_bourgeoisie_share
            + self.labor_aristocracy_share
            + self.proletariat_share
            + self.lumpenproletariat_share
        )
        return abs(total - 1.0) <= 0.001

    def dynamic_shares(self) -> tuple[float, float, float]:
        """Return the three dynamic class shares for engine operations.

        Returns:
            Tuple of (LA, proletariat, lumpen) shares.
        """
        return (
            self.labor_aristocracy_share,
            self.proletariat_share,
            self.lumpenproletariat_share,
        )

    def with_updated_dynamics(
        self,
        la: float,
        prol: float,
        lumpen: float,
    ) -> ClassDistribution:
        """Return new distribution with updated dynamic shares.

        Preserves bourgeoisie and petit-bourgeoisie shares. Increments
        year by 1 (one simulation period = one year).

        Args:
            la: New labor aristocracy share.
            prol: New proletariat share.
            lumpen: New lumpenproletariat share.

        Returns:
            New ClassDistribution with year + 1.
        """
        return ClassDistribution(
            fips=self.fips,
            year=self.year + 1,
            bourgeoisie_share=self.bourgeoisie_share,
            petit_bourgeoisie_share=self.petit_bourgeoisie_share,
            labor_aristocracy_share=la,
            proletariat_share=prol,
            lumpenproletariat_share=lumpen,
        )


class EconomicConditions(BaseModel):
    """Aggregate economic state for a county-year.

    Input to the transition engine. Contains all economic indicators needed
    to compute transition rates for one simulation period.

    Args:
        fips: County FIPS code.
        year: Calendar year.
        unemployment_rate: Local unemployment rate [0, 1].
        median_wage: Median annual wage in dollars.
        melt: MELT ($/labor-hour) from Feature 013.
        phi_hour: Imperial rent per hour ($) from Feature 013.
        foreclosure_rate: Annual foreclosure filing rate [0, 1].
        bankruptcy_rate: Annual personal bankruptcy rate [0, 1].
        eviction_rate: Annual eviction filing rate (renters) [0, 1].
        crisis: True if TRPF or exogenous crisis is active.

    Example:
        >>> cond = EconomicConditions(
        ...     fips="26163", year=2010, unemployment_rate=0.15,
        ...     median_wage=35000.0, melt=62.0, phi_hour=3.50,
        ...     foreclosure_rate=0.046, bankruptcy_rate=0.013,
        ...     eviction_rate=0.070, crisis=True,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2030, description="Calendar year")
    unemployment_rate: float = Field(..., ge=0.0, le=1.0, description="Local unemployment rate")
    median_wage: float = Field(..., ge=0.0, description="Median annual wage ($)")
    melt: float = Field(..., gt=0.0, description="MELT ($/labor-hour)")
    phi_hour: float = Field(..., ge=0.0, description="Imperial rent per hour ($)")
    foreclosure_rate: float = Field(..., ge=0.0, le=1.0, description="Annual foreclosure rate")
    bankruptcy_rate: float = Field(..., ge=0.0, le=1.0, description="Annual bankruptcy rate")
    eviction_rate: float = Field(..., ge=0.0, le=1.0, description="Annual eviction rate")
    crisis: bool = Field(..., description="True if crisis conditions active")


class TransitionRates(BaseModel):
    """Sparse transition structure for the three dynamic classes.

    Four named pathways map to specific economic mechanisms. All rates
    are non-negative and clamped to [0, 1].

    Args:
        fips: County FIPS code.
        year: Calendar year.
        dispossession: LA -> Proletariat rate.
        accumulation: Proletariat -> LA rate.
        precaritization: Proletariat -> Lumpen rate.
        stabilization: Lumpen -> Proletariat rate.

    Example:
        >>> rates = TransitionRates(
        ...     fips="00000", year=2015,
        ...     dispossession=0.01, accumulation=0.005,
        ...     precaritization=0.02, stabilization=0.05,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2030, description="Calendar year")
    dispossession: float = Field(..., ge=0.0, le=1.0, description="LA -> Proletariat rate")
    accumulation: float = Field(..., ge=0.0, le=1.0, description="Proletariat -> LA rate")
    precaritization: float = Field(..., ge=0.0, le=1.0, description="Proletariat -> Lumpen rate")
    stabilization: float = Field(..., ge=0.0, le=1.0, description="Lumpen -> Proletariat rate")


class AccumulationResult(BaseModel):
    """Computed wealth change rate for a given economic scenario.

    Args:
        wage: Annual wage income ($).
        consumption: Annual consumption ($).
        savings_rate: Effective savings rate (base + phi_adjustment).
        phi_adjustment: Imperial rent savings boost.
        annual_accumulation: Net annual wealth change ($), may be negative.
        years_to_threshold: Years to reach LA wealth threshold (None if negative).

    Example:
        >>> result = AccumulationResult(
        ...     wage=60000.0, consumption=50000.0, savings_rate=0.15,
        ...     phi_adjustment=0.03, annual_accumulation=1500.0,
        ...     years_to_threshold=94.7,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    wage: float = Field(..., ge=0.0, description="Annual wage income ($)")
    consumption: float = Field(..., ge=0.0, description="Annual consumption ($)")
    savings_rate: float = Field(..., ge=0.0, le=1.0, description="Effective savings rate")
    phi_adjustment: float = Field(..., ge=0.0, description="Imperial rent savings boost")
    annual_accumulation: float = Field(..., description="Net annual wealth change ($)")
    years_to_threshold: float | None = Field(
        default=None, description="Years to LA threshold (None if negative accumulation)"
    )


class DispossessionRisk(BaseModel):
    """Composite dispossession risk from multiple data sources.

    Produces pathway-specific rates using composite weighting from
    research.md section 3a.

    Args:
        fips: County FIPS code.
        year: Calendar year.
        foreclosure_risk: Foreclosure probability.
        bankruptcy_risk: Bankruptcy probability.
        eviction_risk: Eviction probability.
        la_to_p_rate: Weighted LA -> Proletariat dispossession rate.
        p_to_l_component: Weighted P -> Lumpen dispossession component.
        foreclosure_available: True if foreclosure data was available.
        bankruptcy_available: True if bankruptcy data was available.
        eviction_available: True if eviction data was available.

    Example:
        >>> risk = DispossessionRisk(
        ...     fips="26163", year=2015,
        ...     foreclosure_risk=0.006, bankruptcy_risk=0.006,
        ...     eviction_risk=0.063, la_to_p_rate=0.01,
        ...     p_to_l_component=0.04,
        ...     foreclosure_available=True, bankruptcy_available=True,
        ...     eviction_available=True,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips: str = Field(..., min_length=5, max_length=5, description="County FIPS code")
    year: int = Field(..., ge=2007, le=2030, description="Calendar year")
    foreclosure_risk: float = Field(..., ge=0.0, le=1.0, description="Foreclosure probability")
    bankruptcy_risk: float = Field(..., ge=0.0, le=1.0, description="Bankruptcy probability")
    eviction_risk: float = Field(..., ge=0.0, le=1.0, description="Eviction probability")
    la_to_p_rate: float = Field(..., ge=0.0, le=1.0, description="Weighted LA->P rate")
    p_to_l_component: float = Field(..., ge=0.0, le=1.0, description="Weighted P->L component")
    foreclosure_available: bool = Field(..., description="Foreclosure data available")
    bankruptcy_available: bool = Field(..., description="Bankruptcy data available")
    eviction_available: bool = Field(..., description="Eviction data available")


class SavingsRateSchedule(BaseModel):
    """Class-based step function for savings rates.

    Maps each ClassPosition name to a base savings rate. Calibrated
    against Fed SCF data (Saez & Zucman 2020).

    Args:
        rates: ClassPosition name -> base savings rate.
        phi_cap: Maximum imperial rent adjustment (default 0.05).

    Example:
        >>> schedule = SavingsRateSchedule(
        ...     rates={"BOURGEOISIE": 0.38, "PROLETARIAT": 0.03, ...},
        ...     phi_cap=0.05,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    rates: dict[str, float] = Field(..., description="ClassPosition name -> base savings rate")
    phi_cap: float = Field(
        default=0.05, ge=0.0, le=0.10, description="Maximum imperial rent adjustment"
    )


__all__ = [
    "AccumulationResult",
    "ClassDistribution",
    "DispossessionRisk",
    "EconomicConditions",
    "SavingsRateSchedule",
    "TransitionRates",
]
