"""Type definitions for the D-P-D' Lifecycle Circuit.

Feature: 030-dpd-lifecycle-circuit
Date: 2026-02-27

Frozen Pydantic models for population cohort state, legitimation indices,
inheritance flows, and class mobility parameters.

Models:
    - DPDState: Per-county population distribution across D/P/D' phases
    - LegitimationState: Weighted legitimation index components
    - InheritanceFlow: Pareto-distributed intergenerational wealth transfer
    - ClassMobilityParams: Chetty-derived class mobility coefficients

See Also:
    :mod:`babylon.models.types`: Probability, Currency, Gini, Coefficient
    :mod:`babylon.economics.dynamics.types`: ClassDistribution (Feature 016)
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.types import Currency, Gini, Probability


class DPDState(BaseModel):
    """Per-county population distribution across lifecycle phases.

    Tracks population in three phases per tick:
    - D (Dependent): Pre-productive, receives socialization
    - P (Productive): Sells labor-power
    - D' (Dependent'): Post-productive, legitimation bargain

    Args:
        pop_d: Population in D phase (pre-productive).
        pop_p: Population in P phase (productive).
        pop_d_prime: Population in D' phase (post-productive).
        rate_d_to_p: Annual transition rate D → P.
        rate_p_to_d_prime: Annual transition rate P → D'.
        rate_d_prime_to_death: Annual mortality rate in D'.
        birth_rate: Births per P-phase person per tick.
        wealth_d_prime: Aggregate wealth held by D' cohort.

    Example:
        >>> state = DPDState(
        ...     pop_d=2150.0, pop_p=6050.0, pop_d_prime=1800.0,
        ...     rate_d_to_p=0.0556, rate_p_to_d_prime=0.0213,
        ...     rate_d_prime_to_death=0.039, birth_rate=0.0107,
        ...     wealth_d_prime=10_000_000.0,
        ... )
        >>> state.total_population
        10000.0
    """

    model_config = ConfigDict(frozen=True)

    pop_d: float = Field(..., ge=0.0, description="Population in D phase (pre-productive)")
    pop_p: float = Field(..., ge=0.0, description="Population in P phase (productive)")
    pop_d_prime: float = Field(..., ge=0.0, description="Population in D' phase (post-productive)")
    rate_d_to_p: float = Field(..., ge=0.0, le=1.0, description="Annual transition rate D → P")
    rate_p_to_d_prime: float = Field(
        ..., ge=0.0, le=1.0, description="Annual transition rate P → D'"
    )
    rate_d_prime_to_death: float = Field(
        ..., ge=0.0, le=1.0, description="Annual mortality rate in D'"
    )
    birth_rate: float = Field(..., ge=0.0, le=1.0, description="Births per P-phase person per tick")
    wealth_d_prime: Currency = Field(default=0.0, description="Aggregate wealth held by D' cohort")

    @property
    def total_population(self) -> float:
        """Total population across all phases."""
        return self.pop_d + self.pop_p + self.pop_d_prime

    @property
    def dependency_ratio(self) -> float:
        """Ratio of non-productive to productive population.

        Returns inf if pop_p is zero.
        """
        if self.pop_p == 0.0:
            return math.inf
        return (self.pop_d + self.pop_d_prime) / self.pop_p


class LegitimationState(BaseModel):
    """Weighted legitimation index components per county.

    The legitimation index measures how credibly the D' promise is underwritten
    by material conditions. Weight ordering reflects political judgment:
    home_ownership > healthcare > retirement_confidence > pension > ss_replacement.

    Args:
        pension_coverage: Fraction of P-phase with pension access.
        ss_replacement_rate: Social Security replacement ratio.
        healthcare_security: Fraction with secure D' healthcare.
        home_ownership_rate: P-phase home ownership rate.
        retirement_confidence: Subjective D' security assessment.

    Example:
        >>> state = LegitimationState(
        ...     pension_coverage=0.73, ss_replacement_rate=0.43,
        ...     healthcare_security=0.60, home_ownership_rate=0.66,
        ...     retirement_confidence=0.50,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    pension_coverage: Probability = Field(
        ..., description="Fraction of P-phase with pension access"
    )
    ss_replacement_rate: Probability = Field(..., description="Social Security replacement ratio")
    healthcare_security: Probability = Field(..., description="Fraction with secure D' healthcare")
    home_ownership_rate: Probability = Field(..., description="P-phase home ownership rate")
    retirement_confidence: Probability = Field(..., description="Subjective D' security assessment")


class InheritanceFlow(BaseModel):
    """Intergenerational wealth transfer at D' terminus.

    Models Pareto-distributed inheritance from dying D' cohort
    net of care costs consumed during end-of-life.

    Args:
        total_transferred: Total wealth transferred at D' death.
        care_consumed: Wealth consumed by D' care costs.
        net_inheritance: Total minus care costs.
        inheritance_gini: Gini coefficient of inheritance distribution.

    Example:
        >>> flow = InheritanceFlow(
        ...     total_transferred=390_000.0, care_consumed=156_000.0,
        ...     net_inheritance=234_000.0, inheritance_gini=0.5,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    total_transferred: Currency = Field(..., description="Total wealth transferred at D' death")
    care_consumed: Currency = Field(..., description="Wealth consumed by D' care costs")
    net_inheritance: Currency = Field(..., description="Net inheritance (total - care costs)")
    inheritance_gini: Gini = Field(..., description="Gini coefficient of inheritance distribution")

    @model_validator(mode="after")
    def _validate_care_costs(self) -> InheritanceFlow:
        """Care consumed cannot exceed total transferred."""
        if self.care_consumed > self.total_transferred + 0.01:
            msg = (
                f"Care consumed ({self.care_consumed}) exceeds "
                f"total transferred ({self.total_transferred})"
            )
            raise ValueError(msg)
        return self


class ClassMobilityParams(BaseModel):
    """Chetty-derived class mobility parameters per county.

    Static parameters set at initialization, read-only during simulation.
    Encodes Opportunity Atlas mobility rates with racial and carceral modifiers.

    Args:
        mobility_base_rate: KFR pooled at P25 (default 0.445).
        mobility_base_rate_p75: KFR pooled at P75 (default 0.580).
        mobility_racial_gap: Black-White KFR gap (default 0.134).
        carceral_modifier: Incarceration rate multiplier (>1.0, up to 10).
        early_mortality_modifier: Premature death multiplier (>1.0, up to 10).
        baseline_gini: County Gini coefficient.
        poverty_share: Fraction below poverty line.
        employment_rate: Employment-to-population ratio.
        single_parent_fraction: Single-parent household share.
        college_rate: College graduation rate.

    Example:
        >>> params = ClassMobilityParams(
        ...     mobility_base_rate=0.445, mobility_base_rate_p75=0.580,
        ...     mobility_racial_gap=0.134, carceral_modifier=2.8,
        ...     early_mortality_modifier=1.24, baseline_gini=0.485,
        ...     poverty_share=0.126, employment_rate=0.60,
        ...     single_parent_fraction=0.234, college_rate=0.33,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    mobility_base_rate: float = Field(
        default=0.445, ge=0.0, le=1.0, description="KFR pooled at P25"
    )
    mobility_base_rate_p75: float = Field(
        default=0.580, ge=0.0, le=1.0, description="KFR pooled at P75"
    )
    mobility_racial_gap: float = Field(
        default=0.134, ge=0.0, le=1.0, description="Black-White KFR gap"
    )
    # These use float with ge/le because Coefficient is [0,1] but these exceed 1.0
    carceral_modifier: float = Field(
        default=2.8, ge=0.0, le=10.0, description="Incarceration rate multiplier"
    )
    early_mortality_modifier: float = Field(
        default=1.24, ge=0.0, le=10.0, description="Premature death multiplier"
    )
    baseline_gini: Gini = Field(
        default=0.485, description="County Gini coefficient (Chetty Table 8)"
    )
    poverty_share: Probability = Field(
        default=0.126, description="Fraction below poverty line (Chetty Table 8)"
    )
    employment_rate: Probability = Field(
        default=0.60, description="Employment-to-population ratio (Chetty Table 8)"
    )
    single_parent_fraction: Probability = Field(
        default=0.234, description="Single-parent household share (Chetty Table 8)"
    )
    college_rate: Probability = Field(
        default=0.33, description="College graduation rate (Chetty Table 8)"
    )

    @model_validator(mode="after")
    def _validate_mobility_ordering(self) -> ClassMobilityParams:
        """P75 outcome must be >= P25 outcome; gap cannot exceed base."""
        if self.mobility_base_rate > self.mobility_base_rate_p75 + 0.001:
            msg = (
                f"mobility_base_rate ({self.mobility_base_rate}) > "
                f"mobility_base_rate_p75 ({self.mobility_base_rate_p75})"
            )
            raise ValueError(msg)
        if self.mobility_racial_gap > self.mobility_base_rate + 0.001:
            msg = (
                f"mobility_racial_gap ({self.mobility_racial_gap}) > "
                f"mobility_base_rate ({self.mobility_base_rate})"
            )
            raise ValueError(msg)
        return self


__all__ = [
    "ClassMobilityParams",
    "DPDState",
    "InheritanceFlow",
    "LegitimationState",
]
